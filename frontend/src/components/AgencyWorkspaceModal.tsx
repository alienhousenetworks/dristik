import React, { useState, useEffect } from 'react';

interface AgencyClientAccount {
  client_id: string;
  client_name: string;
  domain: string;
  tier: string;
  status: string;
  last_audit_date: string;
  human_score: number;
  google_score: number;
  ai_citation_score: number;
  overall_health: number;
  total_findings: number;
  monthly_budget_inr: number;
  white_label_enabled: boolean;
}

interface AgencyWorkspaceSummary {
  agency_id: string;
  agency_name: string;
  plan_tier: string;
  total_managed_domains: number;
  max_domain_allowance: number;
  average_portfolio_citation_score: number;
  branding: {
    agency_name: string;
    agency_logo_url?: string;
    brand_primary_hex: string;
    hide_dristik_branding: boolean;
    custom_cname?: string;
  };
  clients: AgencyClientAccount[];
  monthly_report_schedule: string;
}

interface AgencyWorkspaceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectClientDomain?: (domain: string) => void;
}

export function AgencyWorkspaceModal({ isOpen, onClose, onSelectClientDomain }: AgencyWorkspaceModalProps) {
  const [data, setData] = useState<AgencyWorkspaceSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [newClientName, setNewClientName] = useState('');
  const [newClientDomain, setNewClientDomain] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const fetchAgency = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/intelligence/agency');
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error('Failed to load agency workspace:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchAgency();
    }
  }, [isOpen]);

  const handleAddClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClientName || !newClientDomain) return;

    try {
      const res = await fetch('/api/v1/intelligence/agency/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: newClientName,
          domain: newClientDomain
        })
      });
      if (res.ok) {
        setNewClientName('');
        setNewClientDomain('');
        setIsAdding(false);
        fetchAgency();
      }
    } catch (err) {
      console.error('Failed to add client:', err);
    }
  };

  const handleDeleteClient = async (clientId: string) => {
    try {
      const res = await fetch(`/api/v1/intelligence/agency/clients/${clientId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchAgency();
      }
    } catch (err) {
      console.error('Failed to remove client:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto scrim p-4 flex flex-col items-center justify-center">
      <div className="sheet border border-line rounded-xl max-w-5xl w-full p-6 space-y-6 max-h-[90vh] overflow-y-auto shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-[0.04em] px-2 py-0.5 rounded bg-paper-200 text-ink-700 border border-line font-mono">
                Agency Mode Workspace
              </span>
              <span className="text-xs text-ink-500 font-mono">
                {data?.plan_tier || 'Plan not loaded'}
              </span>
            </div>
            <h3 className="text-xl font-sans text-ink tracking-tight">
              {data?.agency_name || 'Agency workspace'}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-ink-500 hover:text-ink text-xl font-bold px-2 py-1 rounded"
          >
            ✕
          </button>
        </div>

        {/* Portfolio Stats Bar */}
        {data && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-paper-50 p-4 rounded-lg border border-line">
            <div>
              <span className="text-[10px] uppercase font-bold text-ink-500 block">Managed Clients</span>
              <span className="text-xl font-bold font-mono text-ink mt-0.5 block">
                {data.total_managed_domains} / {data.max_domain_allowance}
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-ink-500 block">Avg AI Citation Score</span>
              <span className="text-xl font-bold font-mono text-good mt-0.5 block">
                {data.average_portfolio_citation_score} / 100
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-ink-500 block">White-Label Branding</span>
              <span className="text-xs font-bold text-ink-700 mt-1 block">
                {data.branding.hide_dristik_branding ? '✓ Active (100% Unbranded)' : 'Inactive'}
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-ink-500 block">Custom Client CNAME</span>
              <span className="text-xs font-mono text-ink-700 mt-1 block truncate">
                {data.branding.custom_cname}
              </span>
            </div>
          </div>
        )}

        {/* Add Client Toggle / Form */}
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-[0.04em] text-ink-500">
            Client Accounts (Client A, B, C, D, E)
          </span>
          <button
            type="button"
            onClick={() => setIsAdding(!isAdding)}
            className="btn-primary text-white font-semibold text-xs px-3 py-1.5 rounded transition flex items-center gap-1.5"
          >
            <span>+</span>
            <span>Add Client Domain</span>
          </button>
        </div>

        {isAdding && (
          <form onSubmit={handleAddClient} className="bg-paper-50 p-4 rounded-lg border border-line space-y-3">
            <span className="text-xs font-bold text-ink block">Provision New Managed Client</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Client Name (e.g. Zenobia Cloud)"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                className="bg-sheet border border-line rounded px-3 py-2 text-xs text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine"
                required
              />
              <input
                type="text"
                placeholder="Target Domain (e.g. zenobiacloud.com)"
                value={newClientDomain}
                onChange={(e) => setNewClientDomain(e.target.value)}
                className="bg-sheet border border-line rounded px-3 py-2 text-xs text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                required
              />
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setIsAdding(false)}
                className="px-3 py-1.5 border border-line rounded text-xs text-ink-700 hover:text-ink"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 bg-good hover:opacity-90 text-white rounded text-xs font-bold"
              >
                Provision Client
              </button>
            </div>
          </form>
        )}

        {/* Client Roster Table or Empty State */}
        {(!data?.clients || data.clients.length === 0) ? (
          <div className="bg-paper-50 border border-line rounded-lg p-10 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-paper-100 border border-line text-ink-700 flex items-center justify-center mx-auto text-xl font-bold">
              🏢
            </div>
            <h4 className="text-base font-sans text-ink">No Managed Clients Yet</h4>
            <p className="text-xs text-ink-500 max-w-md mx-auto">
              Your Agency Workspace is clean. Click <span className="text-ink-700 font-semibold">+ Add Client Domain</span> above to provision and monitor Client A, B, C, D, or E.
            </p>
          </div>
        ) : (
          <div className="border border-line rounded-lg overflow-hidden bg-sheet">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-paper-100 text-ink-500 border-b border-line font-semibold uppercase tracking-[0.04em] text-[10px]">
                  <th className="p-3">Client Account</th>
                  <th className="p-3">Domain</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Human</th>
                  <th className="p-3">Google</th>
                  <th className="p-3 text-good">AI Citation</th>
                  <th className="p-3">Health</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line font-mono">
                {data.clients.map((c) => (
                  <tr key={c.client_id} className="hover:bg-paper-50 transition-colors">
                    <td className="p-3 font-sans font-bold text-ink">{c.client_name}</td>
                    <td className="p-3 text-ink-700 font-medium">{c.domain}</td>
                    <td className="p-3 font-sans">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-good/10 text-good border border-good/30">
                        {c.status}
                      </span>
                    </td>
                    <td className="p-3 text-ink-700">{c.human_score}</td>
                    <td className="p-3 text-ink-700">{c.google_score}</td>
                    <td className="p-3 font-bold text-good text-sm">{c.ai_citation_score}</td>
                    <td className="p-3 text-ink-700">{c.overall_health}%</td>
                    <td className="p-3 text-right font-sans">
                      <div className="flex items-center justify-end gap-2.5">
                        <button
                          type="button"
                          onClick={() => {
                            if (onSelectClientDomain) {
                              onSelectClientDomain(c.domain);
                              onClose();
                            }
                          }}
                          className="text-xs text-ink-700 font-semibold hover:underline"
                        >
                          Audit →
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteClient(c.client_id)}
                          className="text-ink-500 hover:text-bad transition-colors text-xs font-bold px-1"
                          title="Remove Client"
                        >
                          ✕
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* White-label Deck Generation Notice */}
        <div className="bg-paper-50 border border-line rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div>
            <span className="text-ink font-bold block mb-0.5">Automated White-Label Client Decks</span>
            <span className="text-ink-500">
              Each client report can be branded with your custom agency logo, primary hex color, and delivered without Dristik mentions.
            </span>
          </div>
          <button
            type="button"
            onClick={() => window.print()}
            className="px-3.5 py-1.5 btn-primary text-white rounded font-semibold shrink-0"
          >
            Export White-Label PDF
          </button>
        </div>
      </div>
    </div>
  );
}
