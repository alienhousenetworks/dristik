import React, { useState, useEffect } from 'react';
import { Integration, ConnectorType } from '../types';

interface ConnectorsModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetUrl?: string;
  initialTab?: ConnectorType;
  onIntegrationAdded?: () => void;
}

const GoogleIcon = () => (
  <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
    <path
      fill="#4285F4"
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
    />
    <path
      fill="#34A853"
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
    />
    <path
      fill="#FBBC05"
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
    />
    <path
      fill="#EA4335"
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
    />
  </svg>
);

export const ConnectorsModal: React.FC<ConnectorsModalProps> = ({
  isOpen,
  onClose,
  targetUrl = '',
  initialTab,
  onIntegrationAdded,
}) => {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [activeTab, setActiveTab] = useState<ConnectorType>(initialTab || 'google_search_console');
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Form states
  const [siteUrl, setSiteUrl] = useState(targetUrl || 'https://example.com');
  const [gscSiteUrl, setGscSiteUrl] = useState(targetUrl || '');
  const [gscCredentials, setGscCredentials] = useState('');
  const [gscAuthMode, setGscAuthMode] = useState<'oauth' | 'service_account'>('oauth');
  const [wpUsername, setWpUsername] = useState('');
  const [wpAppPassword, setWpAppPassword] = useState('');
  const [wpPluginKey, setWpPluginKey] = useState('');

  const [ghRepo, setGhRepo] = useState('');
  const [ghToken, setGhToken] = useState('');
  const [ghBranch, setGhBranch] = useState('main');

  const [shopifyUrl, setShopifyUrl] = useState('');
  const [shopifyToken, setShopifyToken] = useState('');

  const [webflowSiteId, setWebflowSiteId] = useState('');
  const [webflowToken, setWebflowToken] = useState('');
  const [wpAuthMode, setWpAuthMode] = useState<'app_password' | 'plugin'>('app_password');

  const fetchIntegrations = async () => {
    try {
      const res = await fetch('/api/v1/connectors');
      if (res.ok) {
        const data = await res.json();
        setIntegrations(data);
      }
    } catch (e) {
      console.error('Failed to load integrations', e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchIntegrations();
      if (targetUrl) {
        setSiteUrl(targetUrl);
        setGscSiteUrl(targetUrl);
      }
      if (initialTab) {
        setActiveTab(initialTab);
      }
    }
  }, [isOpen, targetUrl, initialTab]);

  // Listen for Google OAuth callback from popup window
  useEffect(() => {
    const handleMessage = async (e: MessageEvent) => {
      if (e.data && e.data.type === 'GSC_OAUTH_SUCCESS') {
        setStatusMessage(`✓ Google Search Console connected via 1-Click Google OAuth (${e.data.email || 'Verified'})!`);
        await fetchIntegrations();
        onIntegrationAdded?.();
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleGoogleOAuth = () => {
    setLoading(true);
    setStatusMessage(null);
    const cleanDomain = (gscSiteUrl || siteUrl || 'example.com').replace('https://', '').replace('http://', '').split('/')[0];
    const width = 520;
    const height = 660;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    const authUrl = `/api/v1/connectors/google/oauth/authorize?domain=${encodeURIComponent(cleanDomain)}`;
    const popup = window.open(
      authUrl,
      'google_oauth_popup',
      `width=${width},height=${height},left=${left},top=${top},status=no,resizable=yes`
    );

    const timer = setInterval(async () => {
      if (!popup || popup.closed) {
        clearInterval(timer);
        setLoading(false);
        await fetchIntegrations();
        onIntegrationAdded?.();
      }
    }, 1000);
  };

  const handleQuickConnect = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const cleanDomain = (gscSiteUrl || siteUrl || 'example.com').replace('https://', '').replace('http://', '').split('/')[0];
      const res = await fetch('/api/v1/connectors/google/oauth/quick-connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: cleanDomain,
          property_url: `https://${cleanDomain}`,
          account_email: `owner@${cleanDomain}`
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMessage(`✓ ${data.message}`);
        await fetchIntegrations();
        onIntegrationAdded?.();
      } else {
        setStatusMessage(`Error: ${data.message || 'Connection failed'}`);
      }
    } catch (err: any) {
      setStatusMessage(`Connection failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMessage(null);

    let payload: any = {
      provider: activeTab,
      name: `${activeTab.toUpperCase()} Integration (${siteUrl || ghRepo || 'Site'})`,
      target_url: siteUrl,
    };

    if (activeTab === 'google_search_console') {
      payload.provider = 'google_search_console';
      payload.target_url = gscSiteUrl || siteUrl;
      payload.name = `Google Search Console (${gscSiteUrl || siteUrl})`;
      payload.api_key = gscCredentials;
    } else if (activeTab === 'wordpress') {
      payload.target_url = siteUrl;
      payload.username = wpUsername;
      payload.app_password = wpAppPassword;
      payload.api_key = wpPluginKey;
    } else if (activeTab === 'github') {
      payload.repository = ghRepo;
      payload.github_token = ghToken;
      payload.branch = ghBranch;
      payload.target_url = siteUrl || `https://github.com/${ghRepo}`;
      payload.name = `GitHub: ${ghRepo}`;
    } else if (activeTab === 'shopify') {
      payload.target_url = shopifyUrl;
      payload.api_key = shopifyToken;
    } else if (activeTab === 'webflow') {
      payload.target_url = webflowSiteId;
      payload.api_key = webflowToken;
    } else {
      payload.target_url = siteUrl;
    }

    try {
      const res = await fetch('/api/v1/connectors/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMessage(`✓ ${data.message}`);
        await fetchIntegrations();
        onIntegrationAdded?.();
      } else {
        setStatusMessage(`Error: ${data.detail || data.message || 'Failed to connect'}`);
      }
    } catch (err: any) {
      setStatusMessage(`Connection failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async (integrationId: string) => {
    try {
      await fetch(`/api/v1/connectors/${integrationId}`, { method: 'DELETE' });
      await fetchIntegrations();
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 scrim">
      <div className="relative w-full max-w-4xl sheet border border-line rounded-xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-line bg-paper-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-paper-200 border border-line flex items-center justify-center text-ink">
              <svg className="w-5 h-5 text-pine" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-serif text-ink tracking-tight flex items-center gap-2">
                Connect Platform & Remediation
                <span className="text-[11px] uppercase px-2 py-0.5 rounded bg-good/10 text-good border border-good/30 font-mono">
                  2-Way Sync
                </span>
              </h2>
              <p className="text-xs text-ink-500">
                Connect your website to enable schema deployment, metadata injection, and GitHub PR remediation.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-ink-500 hover:text-ink p-1.5 rounded-lg border border-line bg-paper-50 hover:bg-paper-100 transition"
          >
            ✕
          </button>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Left Column: Platform Tabs & Configuration */}
          <div className="md:col-span-7 space-y-5">
            <div>
              <label className="text-xs font-semibold text-ink-500 uppercase tracking-wider block mb-2">
                Choose Website Architecture
              </label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {[
                  { id: 'google_search_console', label: 'Search Console', icon: 'GSC' },
                  { id: 'wordpress', label: 'WordPress', icon: 'W' },
                  { id: 'github', label: 'GitHub', icon: 'GH' },
                  { id: 'shopify', label: 'Shopify', icon: 'S' },
                  { id: 'webflow', label: 'Webflow', icon: 'WF' },
                  { id: 'generic', label: 'Generic', icon: 'URL' },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setActiveTab(item.id as ConnectorType)}
                    className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-medium transition ${
                      activeTab === item.id
                        ? 'bg-paper-100 border-ink text-ink font-semibold shadow-xs'
                        : 'bg-paper-50 border-line text-ink-700 hover:border-ink-500'
                    }`}
                  >
                    <span className="font-mono text-sm font-bold mb-1">{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleConnect} className="space-y-4 bg-paper-50 p-5 rounded-lg border border-line">
              {/* Google Search Console Form */}
              {activeTab === 'google_search_console' && (
                <div className="space-y-4">
                  {/* Mode Selector */}
                  <div className="grid grid-cols-2 gap-2 p-1 bg-paper-100 rounded border border-line text-xs">
                    <button
                      type="button"
                      onClick={() => setGscAuthMode('oauth')}
                      className={`py-1.5 px-3 rounded font-medium text-center transition ${
                        gscAuthMode === 'oauth'
                          ? 'sheet text-ink border border-line shadow-xs font-semibold'
                          : 'text-ink-500 hover:text-ink'
                      }`}
                    >
                      Method 1: 1-Click Google OAuth (Non-Tech)
                    </button>
                    <button
                      type="button"
                      onClick={() => setGscAuthMode('service_account')}
                      className={`py-1.5 px-3 rounded font-medium text-center transition ${
                        gscAuthMode === 'service_account'
                          ? 'sheet text-ink border border-line shadow-xs font-semibold'
                          : 'text-ink-500 hover:text-ink'
                      }`}
                    >
                      Method 2: Service Account JSON (Enterprise)
                    </button>
                  </div>

                  <div>
                    <label className="text-xs text-ink-700 font-medium block mb-1">Search Console Property / Domain</label>
                    <input
                      type="text"
                      value={gscSiteUrl}
                      onChange={(e) => setGscSiteUrl(e.target.value)}
                      placeholder="https://example.com or sc-domain:example.com"
                      className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                      required
                    />
                  </div>

                  {gscAuthMode === 'oauth' ? (
                    <div className="space-y-3 pt-1">
                      <div className="bg-paper-100 p-4 rounded-xl border border-line text-xs text-ink-700 space-y-3">
                        <div className="flex items-start gap-2.5">
                          <GoogleIcon />
                          <div>
                            <span className="text-ink font-bold block">1-Click Google Sign-In:</span>
                            <p className="text-ink-500 text-[11px] leading-relaxed mt-0.5">
                              Simply sign in with the Google account that manages this website. No Google Cloud Console, private keys, or code needed.
                            </p>
                          </div>
                        </div>

                        <div className="space-y-2 pt-1">
                          <button
                            type="button"
                            onClick={handleGoogleOAuth}
                            disabled={loading}
                            className="w-full py-3 px-4 rounded-xl bg-paper-50 hover:bg-paper-100 border border-line text-ink font-semibold text-xs shadow-xs transition-all flex items-center justify-center gap-2.5 hover:border-ink-500 cursor-pointer disabled:opacity-60"
                          >
                            <GoogleIcon />
                            <span>{loading ? 'Waiting for Google Authorization...' : 'Sign in with Google Search Console'}</span>
                          </button>

                          <button
                            type="button"
                            onClick={handleQuickConnect}
                            disabled={loading}
                            className="w-full py-2 px-4 rounded-xl bg-pine text-paper-50 hover:bg-pine-700 font-semibold text-xs transition-all flex items-center justify-center gap-2 cursor-pointer shadow-2xs disabled:opacity-60"
                          >
                            <span>⚡</span>
                            <span>1-Click Instant Connect (Local / Demo)</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3 pt-1">
                      <div className="text-[11px] text-ink-500 space-y-1 bg-paper-100 p-3 rounded-xl border border-line">
                        <strong className="text-ink block">Service Account Setup:</strong>
                        <p>1. In Google Cloud Console, create a Service Account and generate a JSON key.</p>
                        <p>2. In Google Search Console, go to <strong>Settings &gt; Users & Permissions</strong> and add the service account email as a <em>Full</em> or <em>Owner</em> user.</p>
                      </div>

                      <div>
                        <label className="text-xs text-ink-700 font-medium block mb-1">Service Account JSON / Key</label>
                        <textarea
                          rows={4}
                          value={gscCredentials}
                          onChange={(e) => setGscCredentials(e.target.value)}
                          placeholder={`{\n  "type": "service_account",\n  "client_email": "dristik-gsc@project.iam.gserviceaccount.com",\n  "private_key": "-----BEGIN PRIVATE KEY-----\\n..."\n}`}
                          className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-xs text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                          required
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* WordPress Form */}
              {activeTab === 'wordpress' && (
                <div className="space-y-4">
                  <div className="text-xs text-ink-700 leading-relaxed bg-paper-100 p-3 rounded border border-line">
                    <span className="text-ink font-semibold">WordPress Connector:</span> Grants permission to read pages and inject Schema.org JSON-LD, metadata, and robots.txt. Arbitrary PHP & DB access are strictly blocked.
                  </div>

                  {/* Mode Selector */}
                  <div className="grid grid-cols-2 gap-2 p-1 bg-paper-100 rounded border border-line text-xs">
                    <button
                      type="button"
                      onClick={() => setWpAuthMode('app_password')}
                      className={`py-1.5 px-3 rounded font-medium text-center transition ${
                        wpAuthMode === 'app_password'
                          ? 'sheet text-ink border border-line shadow-xs font-semibold'
                          : 'text-ink-500 hover:text-ink'
                      }`}
                    >
                      Method 1: Application Password
                    </button>
                    <button
                      type="button"
                      onClick={() => setWpAuthMode('plugin')}
                      className={`py-1.5 px-3 rounded font-medium text-center transition ${
                        wpAuthMode === 'plugin'
                          ? 'sheet text-ink border border-line shadow-xs font-semibold'
                          : 'text-ink-500 hover:text-ink'
                      }`}
                    >
                      Method 2: Bridge Plugin (ZIP)
                    </button>
                  </div>

                  <div>
                    <label className="text-xs text-ink-700 font-medium block mb-1">WordPress Site URL</label>
                    <input
                      type="url"
                      value={siteUrl}
                      onChange={(e) => setSiteUrl(e.target.value)}
                      placeholder="https://mywordpress.com"
                      className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine"
                      required
                    />
                  </div>

                  {wpAuthMode === 'app_password' ? (
                    <div className="space-y-3 pt-1">
                      <div className="bg-paper-100 p-3 rounded border border-line text-[11px] text-ink-700 space-y-1">
                        <span className="text-ink font-bold block">How to get an Application Password in WordPress:</span>
                        <p>1. Open your WordPress Admin (<code className="text-pine font-mono font-semibold">/wp-admin</code>) and go to <strong className="text-ink">Users &gt; Profile</strong>.</p>
                        <p>2. Scroll down to <strong className="text-ink">Application Passwords</strong>, type "Dristik" in the box, and click <strong className="text-ink">Add New Application Password</strong>.</p>
                        <p>3. WordPress will give you a 16-character code (e.g. <code className="text-ink-700 font-mono">abcd efgh ijkl mnop</code>). Paste it below.</p>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs text-ink-700 font-medium block mb-1">Admin Username</label>
                          <input
                            type="text"
                            value={wpUsername}
                            onChange={(e) => setWpUsername(e.target.value)}
                            placeholder="admin"
                            className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine"
                            required
                          />
                        </div>
                        <div>
                          <label className="text-xs text-ink-700 font-medium block mb-1">Application Password</label>
                          <input
                            type="password"
                            value={wpAppPassword}
                            onChange={(e) => setWpAppPassword(e.target.value)}
                            placeholder="xxxx xxxx xxxx xxxx"
                            className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                            required
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3 pt-1">
                      <div className="bg-paper-100 p-3 rounded border border-line text-[11px] text-ink-700 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-ink font-bold">Use the Dristik Bridge Plugin if hosting blocks application passwords:</span>
                          <a
                            href="/api/v1/connectors/wordpress/download-plugin"
                            download="dristik-bridge.zip"
                            className="btn-primary text-white font-medium px-2.5 py-1 rounded text-[11px] inline-flex items-center gap-1 transition shrink-0"
                          >
                            <span>📥</span>
                            Download Plugin (.zip)
                          </a>
                        </div>
                        <p>1. Download the ZIP file above.</p>
                        <p>2. In your WordPress Admin, go to <strong className="text-ink">Plugins &gt; Add New &gt; Upload Plugin</strong>, choose the file and click <strong className="text-ink">Activate</strong>.</p>
                        <p>3. Go to <strong className="text-ink">Settings &gt; Dristik AI Bridge</strong> in WordPress, copy your API Key, and paste it below.</p>
                      </div>

                      <div>
                        <label className="text-xs text-ink-700 font-medium block mb-1">Dristik Bridge Plugin API Key</label>
                        <input
                          type="text"
                          value={wpPluginKey}
                          onChange={(e) => setWpPluginKey(e.target.value)}
                          placeholder="dstk_live_..."
                          className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono text-xs"
                          required
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* GitHub Form */}
              {activeTab === 'github' && (
                <div className="space-y-3">
                  <div className="text-xs text-ink-700 leading-relaxed bg-paper-100 p-3 rounded border border-line">
                    <span className="text-ink font-semibold">GitHub Connector:</span> Works with Next.js, React, Vite, and Remix. Dristik will create isolated branches (<code className="text-pine font-mono">dristik/fix-*</code>) and submit Pull Requests with before/after diffs.
                  </div>
                  <div>
                    <label className="text-xs text-ink-700 font-medium block mb-1">Repository (owner/repo)</label>
                    <input
                      type="text"
                      value={ghRepo}
                      onChange={(e) => setGhRepo(e.target.value)}
                      placeholder="acme-corp/website"
                      className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-ink-700 font-medium block mb-1">Personal Access Token</label>
                      <input
                        type="password"
                        value={ghToken}
                        onChange={(e) => setGhToken(e.target.value)}
                        placeholder="ghp_••••••••••••"
                        className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-ink-700 font-medium block mb-1">Target Branch</label>
                      <input
                        type="text"
                        value={ghBranch}
                        onChange={(e) => setGhBranch(e.target.value)}
                        placeholder="main"
                        className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Shopify Form */}
              {activeTab === 'shopify' && (
                <div className="space-y-3">
                  <div className="text-xs text-ink-700 leading-relaxed bg-paper-100 p-3 rounded border border-line">
                    <span className="text-ink font-semibold">Shopify Connector:</span> Manages theme liquid snippets, product schema metafields, and collection SEO tags.
                  </div>
                  <div>
                    <label className="text-xs text-ink-700 font-medium block mb-1">Shopify Store URL</label>
                    <input
                      type="url"
                      value={shopifyUrl}
                      onChange={(e) => setShopifyUrl(e.target.value)}
                      placeholder="https://mybrand.myshopify.com"
                      className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-xs text-ink-700 font-medium block mb-1">Admin API Access Token</label>
                    <input
                      type="password"
                      value={shopifyToken}
                      onChange={(e) => setShopifyToken(e.target.value)}
                      placeholder="shpat_••••••••••••"
                      className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                    />
                  </div>
                </div>
              )}

              {/* Webflow Form */}
              {activeTab === 'webflow' && (
                <div className="space-y-3">
                  <div className="text-xs text-ink-700 leading-relaxed bg-paper-100 p-3 rounded border border-line">
                    <span className="text-ink font-semibold">Webflow Connector:</span> Automatically deploys custom code embeds into the head tag and manages CMS collection SEO fields.
                  </div>
                  <div>
                    <label className="text-xs text-ink-700 font-medium block mb-1">Site ID</label>
                    <input
                      type="text"
                      value={webflowSiteId}
                      onChange={(e) => setWebflowSiteId(e.target.value)}
                      placeholder="64f1a23b90..."
                      className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-xs text-ink-700 font-medium block mb-1">Webflow API Token</label>
                    <input
                      type="password"
                      value={webflowToken}
                      onChange={(e) => setWebflowToken(e.target.value)}
                      placeholder="wfl_••••••••••••"
                      className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                    />
                  </div>
                </div>
              )}

              {/* Generic Website Form */}
              {activeTab === 'generic' && (
                <div className="space-y-3">
                  <div className="text-xs text-ink-700 leading-relaxed bg-paper-100 p-3 rounded border border-line">
                    <span className="text-ink font-semibold">Generic Website (Crawl-Only):</span> Zero credentials required. Dristik audits public HTML and exports ready-to-deploy Developer Patch Packs (ZIP) with 15-minute install guides.
                  </div>
                  <div>
                    <label className="text-xs text-ink-700 font-medium block mb-1">Public Website URL</label>
                    <input
                      type="url"
                      value={siteUrl}
                      onChange={(e) => setSiteUrl(e.target.value)}
                      placeholder="https://example.com"
                      className="w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine"
                      required
                    />
                  </div>
                </div>
              )}

              {statusMessage && (
                <div className={`p-3 rounded text-xs font-mono border ${
                  statusMessage.startsWith('✓') ? 'bg-good/10 border-good/30 text-good' : 'bg-bad/10 border-bad/30 text-bad'
                }`}>
                  {statusMessage}
                </div>
              )}

              {!(activeTab === 'google_search_console' && gscAuthMode === 'oauth') && (
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 btn-primary text-white font-semibold rounded text-sm transition disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
                >
                  {loading ? 'Authenticating & Verifying...' : `Connect ${activeTab.toUpperCase()}`}
                </button>
              )}
            </form>
          </div>

          {/* Right Column: Active Connected Accounts & Health Status */}
          <div className="md:col-span-5 space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-ink-500 uppercase tracking-wider">
                Connected Platforms ({integrations.length})
              </label>
              <button
                onClick={fetchIntegrations}
                className="text-xs text-pine font-medium hover:underline"
              >
                Refresh Status
              </button>
            </div>

            <div className="space-y-3">
              {integrations.length === 0 ? (
                <div className="p-8 text-center bg-paper-50 rounded-lg border border-line text-ink-500 text-xs">
                  No platforms connected yet. Select an architecture on the left to begin.
                </div>
              ) : (
                integrations.map((integ) => (
                  <div
                    key={integ.integration_id}
                    className="p-4 rounded-lg sheet border border-line hover:border-ink-500 transition space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-good"></span>
                        <span className="text-sm font-semibold text-ink truncate max-w-[180px]">
                          {integ.name}
                        </span>
                      </div>
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-paper-100 text-ink-700 border border-line">
                        {integ.provider}
                      </span>
                    </div>

                    <div className="text-xs text-ink-500 truncate">
                      {integ.target_url || integ.repository}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-line text-[11px]">
                      <span className="text-good font-mono">
                        ● {integ.status}
                      </span>
                      <button
                        onClick={() => handleDisconnect(integ.integration_id)}
                        className="text-bad hover:underline transition"
                      >
                        Disconnect
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="p-4 rounded-lg bg-paper-100 border border-line text-xs text-ink-700 space-y-2">
              <div className="font-semibold text-ink flex items-center gap-1.5">
                <span>🛡️ Security Guarantee</span>
              </div>
              <p className="text-[11px] text-ink-500 leading-relaxed">
                Connectors operate within strict least-privilege permissions. Credentials are encrypted in transit and stored in environment isolation, never exposed to public crawlers.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
