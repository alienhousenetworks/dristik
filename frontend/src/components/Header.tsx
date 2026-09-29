import React from 'react';
import { AnalysisRun, AppView, AuthUser } from '../types';
import { can } from '../services/auth';
import { Dropdown, MenuItem, MenuLabel } from './ui';
import { RecentAuditsDropdown } from './RecentAuditsDropdown';

interface HeaderProps {
  run: AnalysisRun | null;
  isLoading: boolean;
  user: AuthUser | null;
  view: AppView;
  onOpenPlans: () => void;
  onOpenConnectors?: () => void;
  onOpenExternal?: () => void;
  onOpenRemediation?: () => void;
  onOpenAgency?: () => void;
  onOpenRubric?: () => void;
  onExport: () => void;
  onView: (view: AppView) => void;
  onLogout: () => void;
  onSelectAudit?: (analysisId: string) => void;
  onNewAudit?: () => void;
  onAuditDeleted?: (analysisId: string) => void | Promise<void>;
}

export function Header({
  run,
  isLoading,
  user,
  view,
  onOpenPlans,
  onOpenConnectors,
  onOpenExternal,
  onOpenRemediation,
  onOpenAgency,
  onOpenRubric,
  onExport,
  onView,
  onLogout,
  onSelectAudit,
  onNewAudit,
  onAuditDeleted,
}: HeaderProps) {
  const status = run?.status?.replace(/_/g, ' ') || '';
  const showTools = Boolean(user && (onOpenConnectors || onOpenExternal || onOpenRemediation || onOpenAgency || onOpenRubric));

  const toolItems = (
    <>
      <MenuLabel>Workspace</MenuLabel>
      {onOpenConnectors && <MenuItem onClick={onOpenConnectors}>Connectors</MenuItem>}
      {onOpenExternal && <MenuItem onClick={onOpenExternal}>External authority</MenuItem>}
      {run?.report && onOpenRemediation && <MenuItem onClick={onOpenRemediation}>Remediation</MenuItem>}
      {onOpenAgency && <MenuItem onClick={onOpenAgency}>Agency workspace</MenuItem>}
      {onOpenRubric && <MenuItem onClick={onOpenRubric}>Scoring rubric</MenuItem>}
      <MenuLabel>Billing</MenuLabel>
      <MenuItem onClick={onOpenPlans}>Pay for an audit</MenuItem>
      {run?.report && view === 'home' && <MenuItem onClick={onExport}>Export PDF</MenuItem>}
    </>
  );

  return (
    <header className="no-print sticky top-0 z-30 topbar border-b border-line">
      <div className="h-14 px-3 sm:px-4 lg:px-6 flex items-center justify-between gap-3">
        <div className="flex items-center gap-4 min-w-0">
          <button type="button" onClick={() => onView('home')} className="flex items-baseline gap-2.5 shrink-0">
            <span className="font-serif text-2xl sm:text-[1.65rem] leading-none text-ink tracking-tight">Dristik</span>
          </button>

          {run && view === 'home' && (
            <div className="hidden md:flex items-center gap-2 min-w-0 text-sm text-ink-500 border-l border-line pl-4">
              <span
                className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  run.status === 'completed' ? 'bg-good' : run.status === 'failed' ? 'bg-bad' : 'bg-pine animate-pulse'
                }`}
              />
              <span className="truncate max-w-[280px] text-ink-700">
                {run.website_url.replace(/^https?:\/\//, '')}
              </span>
              <span className="capitalize">{status}</span>
              {isLoading && <span className="font-mono text-xs">{run.progress_percentage}%</span>}
            </div>
          )}
        </div>

        <nav className="flex items-center gap-1 sm:gap-2 text-sm shrink-0">
          {onSelectAudit && (
            <RecentAuditsDropdown
              currentAnalysisId={run?.analysis_id}
              onSelectAudit={onSelectAudit}
              onNewAudit={onNewAudit}
              onAuditDeleted={onAuditDeleted}
            />
          )}

          {run && onAuditDeleted && view === 'home' && (
            <button
              type="button"
              onClick={() => {
                const label = run.website_url.replace(/^https?:\/\//, '');
                if (!window.confirm(`Delete the audit for ${label}? This cannot be undone.`)) return;
                onAuditDeleted(run.analysis_id);
              }}
              className="inline-flex items-center px-2.5 py-1.5 rounded-lg border border-bad/40 text-bad hover:bg-bad/10 text-xs font-semibold"
              title="Delete this audit"
            >
              Delete audit
            </button>
          )}
          {run && onNewAudit && view === 'home' && (
            <button
              type="button"
              onClick={onNewAudit}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-line hover:border-ink-400 text-xs font-semibold text-ink-700"
              title="Clear current audit and start fresh"
            >
              New audit
            </button>
          )}
          <div className="md:hidden">
            <Dropdown label="More">
              <MenuItem onClick={() => onView('pricing')}>Pricing</MenuItem>
              <MenuItem onClick={() => onView('contact')}>Contact</MenuItem>
              {!user && <MenuItem onClick={() => onView('login')}>Sign in</MenuItem>}
              {showTools && toolItems}
            </Dropdown>
          </div>

          <button
            type="button"
            onClick={() => onView('pricing')}
            className={`hidden md:inline nav-link px-2 py-1 ${view === 'pricing' ? 'is-active' : ''}`}
          >
            Pricing
          </button>
          <button
            type="button"
            onClick={() => onView('contact')}
            className={`hidden md:inline nav-link px-2 py-1 ${view === 'contact' ? 'is-active' : ''}`}
          >
            Contact
          </button>

          {showTools && (
            <div className="hidden md:block">
              <Dropdown label="Tools">{toolItems}</Dropdown>
            </div>
          )}

          {user ? (
            <Dropdown label={user.full_name.split(' ')[0]}>
              <MenuLabel>{user.org_name}</MenuLabel>
              <MenuItem onClick={() => onView('account')}>Account</MenuItem>
              {can(user, 'staff:invite') && <MenuItem onClick={() => onView('team')}>Team</MenuItem>}
              {user.is_system && <MenuItem onClick={() => onView('system')}>Admin console</MenuItem>}
              <MenuItem onClick={onLogout}>Log out</MenuItem>
            </Dropdown>
          ) : (
            <>
              <button type="button" onClick={() => onView('login')} className="hidden md:inline nav-link px-2 py-1">
                Sign in
              </button>
              <button type="button" onClick={() => onView('signup')} className="btn-primary px-2.5 sm:px-3 py-1.5 text-sm">
                Sign up
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
