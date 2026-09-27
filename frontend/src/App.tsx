import React, { useEffect, useState } from 'react';
import { AnalysisRun, AnalysisSummary, AppView, AuthUser, ConnectorType, Finding, TabId } from './types';
import { deleteAnalysis, getAnalysis, listAnalyses, openAnalysisStream, startAnalysis } from './services/api';
import { can, fetchMe, logout } from './services/auth';
import { Header } from './components/Header';
import { AuditForm } from './components/AuditForm';
import { Pipeline } from './components/Pipeline';
import { Telemetry } from './components/Telemetry';
import { Overview } from './components/Overview';
import { Perspectives } from './components/Perspectives';
import { Findings } from './components/Findings';
import { Roadmap } from './components/Roadmap';
import { Report } from './components/Report';
import { Big4AuditReport } from './components/Big4AuditReport';
import { AuditPdfReport } from './components/AuditPdfReport';
import { Pricing } from './components/Pricing';
import { Drawer } from './components/Drawer';
import { PricingModal } from './components/PricingModal';
import { Intro } from './components/Intro';
import { ForgotScreen, LoginScreen, ResetScreen, SignupScreen } from './components/AuthScreens';
import { AccountPanel, TeamPanel } from './components/AccountPanel';
import { ContactForm } from './components/ContactForm';
import { SystemPanel } from './components/SystemPanel';
import { ConnectorsModal } from './components/ConnectorsModal';
import { RemediationFlowModal } from './components/RemediationFlowModal';
import { AgencyWorkspaceModal } from './components/AgencyWorkspaceModal';
import { PillarNavBar } from './components/Navigation/PillarNavBar';
import { SeoWorkspaceView } from './components/Pillars/SeoWorkspaceView';
import { GeoWorkspaceView } from './components/Pillars/GeoWorkspaceView';
import { AeoWorkspaceView } from './components/Pillars/AeoWorkspaceView';
import { CroWorkspaceView } from './components/Pillars/CroWorkspaceView';
import { CompetitorWorkspaceView } from './components/Pillars/CompetitorWorkspaceView';
import { DevPatchPackView } from './components/DevPatchPackView';
import { VerificationWorkspaceView } from './components/VerificationWorkspaceView';
import { Pages } from './components/Pages';
import { ScoringRubricModal } from './components/ScoringRubricModal';
import { RecentAuditsDropdown } from './components/RecentAuditsDropdown';
import { PageHeader } from './components/ui';

const VIEWS = new Set<AppView>([
  'home',
  'pricing',
  'login',
  'signup',
  'forgot',
  'reset',
  'account',
  'contact',
  'team',
  'system',
]);

function parseNavigation(): { view: AppView; token?: string; analysisId?: string } {
  const searchParams = new URLSearchParams(window.location.search);
  const searchAnalysisId = searchParams.get('analysis_id') || undefined;

  const raw = window.location.hash.replace(/^#\/?/, '');
  if (!raw) {
    return {
      view: 'home',
      analysisId: searchAnalysisId || localStorage.getItem('dristik_active_analysis_id') || undefined,
    };
  }
  const [path, qs] = raw.split('?');
  const view = (VIEWS.has(path as AppView) ? path : 'home') as AppView;
  const hashParams = new URLSearchParams(qs || '');
  const token = hashParams.get('token') || undefined;
  const analysisId = hashParams.get('analysis_id') || searchAnalysisId || localStorage.getItem('dristik_active_analysis_id') || undefined;
  return { view, token, analysisId };
}

export function App() {
  const initial = parseNavigation();
  const [url, setUrl] = useState('');
  const [maxPages, setMaxPages] = useState(5);
  const [siteType, setSiteType] = useState<string>('');
  const [declaredNotes, setDeclaredNotes] = useState<string>('');
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [finding, setFinding] = useState<Finding | null>(null);
  const [tab, setTab] = useState<TabId>('overview');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plansOpen, setPlansOpen] = useState(false);
  const [connectorsOpen, setConnectorsOpen] = useState(false);
  const [connectorsInitialTab, setConnectorsInitialTab] = useState<ConnectorType>('google_search_console');
  const [remediationOpen, setRemediationOpen] = useState(false);
  const [agencyOpen, setAgencyOpen] = useState(false);
  const [rubricOpen, setRubricOpen] = useState(false);
  const [planId, setPlanId] = useState('professional');
  const [voucher, setVoucher] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [view, setView] = useState<AppView>(initial.view);
  const [resetToken, setResetToken] = useState<string | undefined>(initial.token);
  const [previewDeck, setPreviewDeck] = useState(false);
  const [recentAudits, setRecentAudits] = useState<AnalysisSummary[]>([]);

  const syncActiveAnalysisId = (id: string | null) => {
    if (id) {
      localStorage.setItem('dristik_active_analysis_id', id);
      const searchParams = new URLSearchParams(window.location.search);
      searchParams.set('analysis_id', id);
      const newUrl = `${window.location.pathname}?${searchParams.toString()}${window.location.hash}`;
      window.history.replaceState(null, '', newUrl);
    } else {
      localStorage.removeItem('dristik_active_analysis_id');
      const searchParams = new URLSearchParams(window.location.search);
      searchParams.delete('analysis_id');
      const queryStr = searchParams.toString();
      const newUrl = queryStr
        ? `${window.location.pathname}?${queryStr}${window.location.hash}`
        : `${window.location.pathname}${window.location.hash}`;
      window.history.replaceState(null, '', newUrl);
    }
  };

  const go = (next: AppView, extra?: string) => {
    if (next === 'home' && !extra) {
      history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
      setView('home');
      return;
    }
    window.location.hash = extra || next;
    const parsed = parseNavigation();
    setView(parsed.view);
    if (parsed.token) setResetToken(parsed.token);
  };

  const loadAudit = async (targetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAnalysis(targetId);
      setRun(data);
      if (data.website_url) setUrl(data.website_url);
      syncActiveAnalysisId(data.analysis_id);

      // If still in progress, reconnect live stream
      if (data.status !== 'completed' && data.status !== 'failed') {
        const stream = openAnalysisStream(data.analysis_id);
        stream.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data);
            setRun((prev) => {
              if (!prev) return prev;
              const liveTelemetry = payload.telemetry ?? payload.data?.telemetry ?? prev.telemetry;
              return {
                ...prev,
                progress_percentage: payload.progress ?? prev.progress_percentage,
                current_step: payload.message ?? prev.current_step,
                status: payload.stage ?? prev.status,
                report: payload.data?.report ?? prev.report,
                telemetry: liveTelemetry,
              };
            });
            if (payload.stage === 'completed') {
              setLoading(false);
              stream.close();
            } else if (payload.stage === 'failed') {
              setLoading(false);
              setError(payload.message || 'The audit failed.');
              stream.close();
            }
          } catch {
            /* ignore */
          }
        };
        stream.onerror = () => {
          getAnalysis(data.analysis_id)
            .then((updated) => {
              setRun(updated);
              setLoading(false);
            })
            .catch(() => setLoading(false));
          stream.close();
        };
      } else {
        setLoading(false);
      }
    } catch (err: unknown) {
      setLoading(false);
      setError(err instanceof Error ? err.message : 'Could not load the audit.');
      syncActiveAnalysisId(null);
    }
  };

  const clearAudit = () => {
    syncActiveAnalysisId(null);
    setRun(null);
    setUrl('');
    setError(null);
    setFinding(null);
    setTab('overview');
  };

  useEffect(() => {
    fetchMe().then(setUser).catch(() => setUser(null));
    listAnalyses(6).then(setRecentAudits).catch(() => {});

    const nav = parseNavigation();
    if (nav.analysisId) {
      loadAudit(nav.analysisId);
    }

    const onHash = () => {
      const parsed = parseNavigation();
      setView(parsed.view);
      setResetToken(parsed.token);
      if (parsed.analysisId && parsed.analysisId !== run?.analysis_id) {
        loadAudit(parsed.analysisId);
      }
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const start = async (overrideUrl?: string) => {
    const target = (overrideUrl ?? url).trim();
    if (!user) {
      setError('Sign in to run an audit.');
      go('login');
      return;
    }
    if (!can(user, 'mission:create')) {
      setError('Your role can view reports but cannot start audits. Ask an admin.');
      return;
    }
    if (!target) {
      setError('Enter a website URL.');
      return;
    }

    setLoading(true);
    setError(null);
    setFinding(null);
    setTab('overview');

    try {
      const created = await startAnalysis(target, maxPages, siteType, declaredNotes);
      setRun(created);
      syncActiveAnalysisId(created.analysis_id);

      const stream = openAnalysisStream(created.analysis_id);
      stream.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setRun((prev) => {
            if (!prev) return prev;
            const liveTelemetry = payload.telemetry ?? payload.data?.telemetry ?? prev.telemetry;
            return {
              ...prev,
              progress_percentage: payload.progress ?? prev.progress_percentage,
              current_step: payload.message ?? prev.current_step,
              status: payload.stage ?? prev.status,
              report: payload.data?.report ?? prev.report,
              telemetry: liveTelemetry,
            };
          });

          if (payload.stage === 'completed') {
            setLoading(false);
            stream.close();
          } else if (payload.stage === 'failed') {
            setLoading(false);
            setError(payload.message || 'The audit failed.');
            stream.close();
          }
        } catch {
          /* ignore malformed events */
        }
      };

      stream.onerror = () => {
        getAnalysis(created.analysis_id)
          .then((data) => {
            setRun(data);
            setLoading(false);
          })
          .catch(() => setLoading(false));
        stream.close();
      };
    } catch (err: unknown) {
      setLoading(false);
      setError(err instanceof Error ? err.message : 'Could not start the audit.');
    }
  };

  const report = run?.report;
  const findingsCount = report?.findings.length ?? 0;
  const pagesCount = report?.crawl_manifest?.pages?.length ?? 0;
  const workspaceRun = view === 'home' ? run : null;

  const auditForm = (
    <AuditForm
      url={url}
      maxPages={maxPages}
      siteType={siteType}
      declaredNotes={declaredNotes}
      isLoading={loading}
      error={error}
      onUrlChange={(value) => {
        setUrl(value);
        setError(null);
      }}
      onMaxPagesChange={setMaxPages}
      onSiteTypeChange={setSiteType}
      onDeclaredNotesChange={setDeclaredNotes}
      onSubmit={() => start()}
    />
  );

  return (
    <div className="min-h-screen text-ink flex flex-col">
      <Header
        run={run}
        isLoading={loading}
        user={user}
        view={view}
        onView={(next) => go(next)}
        onLogout={async () => {
          await logout();
          setUser(null);
          go('home');
        }}
        onOpenPlans={() => setPlansOpen(true)}
        onOpenConnectors={() => {
          setConnectorsInitialTab('wordpress');
          setConnectorsOpen(true);
        }}
        onOpenRemediation={() => setRemediationOpen(true)}
        onOpenAgency={() => setAgencyOpen(true)}
        onOpenRubric={() => setRubricOpen(true)}
        onExport={() => {
          try {
            window.print();
          } catch {
            const id = run?.report?.analysis_id || run?.report?.report_id || run?.analysis_id;
            if (id) window.open(`/api/v1/reports/${id}/executive-deck`, '_blank');
          }
        }}
        onSelectAudit={(id) => loadAudit(id)}
        onNewAudit={clearAudit}
        onAuditDeleted={async (id) => {
          try {
            await deleteAnalysis(id);
            setRecentAudits((prev) => prev.filter((item) => item.analysis_id !== id));
            if (run?.analysis_id === id) clearAudit();
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Could not delete the audit.');
          }
        }}
      />

      {workspaceRun ? (
        <div className="no-print flex-1 flex flex-col lg:flex-row min-h-0">
          {report && (
            <PillarNavBar
              tab={tab}
              onSelectTab={setTab}
              report={report}
              findingsCount={findingsCount}
              pagesCount={pagesCount}
              onNewAudit={clearAudit}
            />
          )}

          <main className="no-print flex-1 min-w-0">
            <div className="max-w-[1100px] mx-auto px-5 sm:px-8 py-8 space-y-6">
              {!report && (
                <div className="space-y-6">
                  <PageHeader
                    kicker="Audit in progress"
                    title={workspaceRun.website_url.replace(/^https?:\/\//, '')}
                    description="Crawl, evidence, specialists, and scoring run in sequence. Stay on this page until the report is ready."
                  />
                  <Pipeline run={workspaceRun} />
                  {workspaceRun.telemetry && <Telemetry telemetry={workspaceRun.telemetry} />}
                  {error && <p className="text-sm text-bad">{error}</p>}
                </div>
              )}

              {report && (
                <div className="space-y-8">
                  {tab === 'overview' && (
                    <Overview
                      scores={report.scores}
                      honestScores={report.honest_scores}
                      profile={report.business_profile}
                      semantic={report.semantic_business}
                      contradictions={report.contradictions}
                      story={report.story_summary}
                      opportunity={report.primary_strategic_opportunity}
                      strengths={report.what_site_gets_right}
                      blockers={report.what_is_holding_it_back}
                      ignore={report.consultant_advice_what_to_ignore}
                      report={report}
                      onNavigate={(nextTab) => {
                        if ((nextTab as string) === 'connectors') {
                          setConnectorsInitialTab('google_search_console');
                          setConnectorsOpen(true);
                        } else {
                          setTab(nextTab);
                        }
                      }}
                      onOpenConnectors={(connectorTab) => {
                        setConnectorsInitialTab((connectorTab as ConnectorType) || 'google_search_console');
                        setConnectorsOpen(true);
                      }}
                    />
                  )}

                  {/* 1. SEO WORKSPACE */}
                  {(tab === 'seo' || tab === 'search_intelligence' || tab === 'search_console') && (
                    <SeoWorkspaceView
                      report={report}
                      analysisId={run?.analysis_id}
                      onSelectFinding={setFinding}
                      onOpenConnectors={(tabId) => {
                        setConnectorsInitialTab((tabId as ConnectorType) || 'google_search_console');
                        setConnectorsOpen(true);
                      }}
                    />
                  )}

                  {/* 2. GEO WORKSPACE */}
                  {(tab === 'geo' || tab === 'ai_search_intelligence' || tab === 'ai_citations' || tab === 'ai_search') && (
                    <GeoWorkspaceView
                      report={report}
                      analysisId={run?.analysis_id}
                      onOpenPatchPack={() => setRemediationOpen(true)}
                      onNavigateToTab={(t) => setTab(t)}
                      onEvaluationsUpdated={(newEvals) => {
                        setRun((prev) => {
                          if (!prev || !prev.report) return prev;
                          return {
                            ...prev,
                            report: {
                              ...prev.report,
                              ai_search_matrix: newEvals,
                            },
                          };
                        });
                      }}
                    />
                  )}

                  {/* 3. AEO WORKSPACE */}
                  {(tab === 'aeo' || tab === 'brand_entity_intelligence') && (
                    <AeoWorkspaceView
                      report={report}
                      analysisId={run?.analysis_id}
                      onOpenPatchPack={() => setRemediationOpen(true)}
                    />
                  )}

                  {/* 4. CRO WORKSPACE */}
                  {(tab === 'cro' || tab === 'conversion_intelligence' || tab === 'website_experience') && (
                    <CroWorkspaceView
                      report={report}
                      analysisId={run?.analysis_id}
                      onDeployRemediation={() => setRemediationOpen(true)}
                    />
                  )}

                  {/* 5. COMPETITOR INTELLIGENCE WORKSPACE */}
                  {(tab === 'competitors' || tab === 'perspectives' || tab === 'lead_gen') && (
                    <CompetitorWorkspaceView
                      report={report}
                      analysisId={run?.analysis_id}
                      websiteUrl={run?.website_url || report.website_url}
                    />
                  )}

                  {/* 6. PAGE INSPECTOR */}
                  {tab === 'pages' && (
                    <Pages
                      manifest={report.crawl_manifest}
                      summary={report.crawl_summary}
                      pageReports={report.page_reports}
                    />
                  )}

                  {/* 7. EVIDENCE LEDGER / FINDINGS */}
                  {tab === 'findings' && <Findings findings={report.findings} onSelect={setFinding} />}

                  {/* 8. DEV PATCH PACK */}
                  {tab === 'patches' && (
                    <DevPatchPackView report={report} analysisId={run?.analysis_id} />
                  )}

                  {/* 9. ACTION ROADMAP */}
                  {tab === 'roadmap' && (
                    <Roadmap
                      days7={report.roadmap_7_days}
                      days30={report.roadmap_30_days}
                      days90={report.roadmap_90_days}
                    />
                  )}

                  {/* 10. VERIFICATION & REGRESSION */}
                  {tab === 'verification' && (
                    <VerificationWorkspaceView report={report} analysisId={run?.analysis_id} />
                  )}

                  {/* 11. PRESENTATION REPORT */}
                  {tab === 'report' && (
                    <Report
                      report={report}
                      onPreviewDeck={() => setPreviewDeck(true)}
                      onExportPdf={() => window.print()}
                    />
                  )}

                  {/* 12. PLANS / BILLING */}
                  {tab === 'plans' && (
                    <Pricing
                      onSelectPlan={(id) => {
                        setPlanId(id);
                        setPlansOpen(true);
                      }}
                    />
                  )}

                  {report.telemetry && (
                    <div className="pt-4 border-t border-line">
                      <Telemetry telemetry={report.telemetry} />
                    </div>
                  )}
                </div>
              )}
            </div>
          </main>
        </div>
      ) : (
        <main className="no-print flex-1 max-w-[1120px] w-full mx-auto px-6 lg:px-8 py-10">
          {view === 'login' && (
            <LoginScreen
              onAuthed={async () => {
                setUser(await fetchMe());
                go('home');
              }}
              onView={go}
            />
          )}
          {view === 'signup' && (
            <SignupScreen
              onAuthed={async () => {
                setUser(await fetchMe());
                go('home');
              }}
              onView={go}
            />
          )}
          {view === 'forgot' && <ForgotScreen onView={go} />}
          {view === 'reset' && <ResetScreen token={resetToken} onView={go} />}
          {view === 'contact' && <ContactForm user={user} />}
          {view === 'account' && user && (
            <AccountPanel
              user={user}
              onDeleted={() => {
                setUser(null);
                go('home');
              }}
            />
          )}
          {(view === 'account' || view === 'team' || view === 'system') && !user && (
            <LoginScreen
              onAuthed={async () => {
                setUser(await fetchMe());
                go(view);
              }}
              onView={go}
            />
          )}
          {view === 'team' && user && <TeamPanel user={user} />}
          {view === 'system' && user?.is_system && <SystemPanel />}
          {view === 'pricing' && (
            <Pricing
              onSelectPlan={(id) => {
                setPlanId(id);
                setPlansOpen(true);
              }}
            />
          )}

          {view === 'home' && (
            <section className="space-y-8">
              <PageHeader
                kicker="Website intelligence"
                title="Evidence-first audits for search, AI, and conversion."
                description="Paste a public URL. Dristik crawls the pages, verifies every claim against the live DOM, then returns a score, findings, patches, and a 7 / 30 / 90-day plan."
              >
                {user ? (
                  <p className="text-sm text-ink-500">
                    Signed in as {user.full_name} · {user.role_label} · {user.org_name}
                  </p>
                ) : (
                  <p className="text-sm text-ink-500">
                    Sign in with your organization to run an audit.{' '}
                    <button type="button" className="text-ink underline" onClick={() => go('signup')}>
                      Create a workspace
                    </button>
                  </p>
                )}
              </PageHeader>

              {voucher && (
                <p className="text-sm text-ink-500">
                  Voucher {voucher} · up to {maxPages} pages
                </p>
              )}

              <div className="card p-5 sm:p-6">
                {auditForm}
                {recentAudits.length > 0 && !run && (
                  <div className="mt-4 pt-3 border-t border-line/60 flex flex-wrap items-center gap-2 text-xs">
                    <span className="text-ink-400 font-medium">Recent audits:</span>
                    {recentAudits.slice(0, 5).map((item) => (
                      <span
                        key={item.analysis_id}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-line/40 text-ink-700 border border-line/40"
                      >
                        <button
                          type="button"
                          onClick={() => loadAudit(item.analysis_id)}
                          className="inline-flex items-center gap-1.5 hover:text-pine font-medium cursor-pointer"
                          title={`Reopen audit for ${item.website_url}`}
                        >
                          <span className="truncate max-w-[140px]">{item.domain || item.website_url.replace(/^https?:\/\//, '')}</span>
                          {item.score_overall != null && (
                            <span className="font-mono text-[10px] px-1 py-0.2 rounded bg-ink/5 text-ink-600">
                              {Math.round(item.score_overall)}
                            </span>
                          )}
                        </button>
                        <button
                          type="button"
                          className="text-[10px] text-ink-400 hover:text-bad px-1"
                          title={`Delete audit for ${item.domain}`}
                          onClick={async () => {
                            const label = item.domain || item.website_url;
                            if (!window.confirm(`Delete the audit for ${label}? This cannot be undone.`)) return;
                            try {
                              await deleteAnalysis(item.analysis_id);
                              setRecentAudits((prev) => prev.filter((row) => row.analysis_id !== item.analysis_id));
                            } catch (err) {
                              setError(err instanceof Error ? err.message : 'Could not delete the audit.');
                            }
                          }}
                        >
                          Delete
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <Intro />
            </section>
          )}
        </main>
      )}

      {report && !previewDeck && (
        <div className="print-only">
          <AuditPdfReport report={report} />
        </div>
      )}

      {previewDeck && report && (
        <div className="scrim fixed inset-0 z-50 overflow-y-auto p-3 sm:p-6 flex flex-col items-center print:static print:p-0 print:overflow-visible print:bg-transparent">
          <div className="w-full max-w-[1400px] my-auto print:max-w-none print:w-full print:my-0">
            <Big4AuditReport
              report={report}
              previewMode
              onPrint={() => {
                try {
                  window.print();
                } catch {
                  const id = report.analysis_id || report.report_id;
                  if (id) window.open(`/api/v1/reports/${id}/executive-deck`, '_blank');
                }
              }}
              onClosePreview={() => setPreviewDeck(false)}
            />
          </div>
        </div>
      )}

      {!workspaceRun && (
        <footer className="no-print border-t border-line mt-auto">
          <div className="max-w-[1120px] mx-auto px-6 lg:px-8 py-6 text-sm text-ink-400 flex items-center justify-between gap-4">
            <span className="font-serif text-lg text-ink-500">Dristik</span>
            <div className="flex items-center gap-5">
              <button type="button" onClick={() => go('contact')} className="hover:text-ink">
                Contact
              </button>
              <span className="hidden sm:inline">Evidence-first website audits</span>
            </div>
          </div>
        </footer>
      )}

      <div className="no-print">
        <Drawer
          finding={finding}
          patches={report?.code_patches || []}
          websiteUrl={report?.website_url}
          analysisId={report?.analysis_id}
          onClose={() => setFinding(null)}
          onOpenConnectors={(connectorTab) => {
            if (connectorTab) setConnectorsInitialTab(connectorTab);
            setConnectorsOpen(true);
          }}
        />
        <PricingModal
          isOpen={plansOpen}
          onClose={() => setPlansOpen(false)}
          targetUrl={url}
          defaultPlanId={planId}
          onUnlocked={(id, code, pages) => {
            setPlanId(id);
            setVoucher(code);
            setMaxPages(pages);
            start(url);
          }}
        />
        <ConnectorsModal
          isOpen={connectorsOpen}
          onClose={() => setConnectorsOpen(false)}
          targetUrl={url || run?.website_url || 'https://example.com'}
          initialTab={connectorsInitialTab}
        />
        <RemediationFlowModal
          isOpen={remediationOpen}
          onClose={() => setRemediationOpen(false)}
          analysisId={run?.analysis_id || 'latest'}
          websiteUrl={run?.website_url || url || 'https://example.com'}
        />
        <AgencyWorkspaceModal
          isOpen={agencyOpen}
          onClose={() => setAgencyOpen(false)}
          onSelectClientDomain={(clientDomain) => {
            setUrl(clientDomain);
            start(clientDomain);
          }}
        />
        <ScoringRubricModal isOpen={rubricOpen} onClose={() => setRubricOpen(false)} />
      </div>
    </div>
  );
}

export default App;
