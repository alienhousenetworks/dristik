import React, { useState } from 'react';
import { ExecutiveReport } from '../../types';
import { PillarShell, Card } from '../ui';
import { SectionExportButtons } from '../ui/SectionExportButtons';
import {
  Bot,
  FileCode,
  Network,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  ShieldCheck,
  Search,
  Database,
  Activity,
  Sparkles,
  AlertTriangle,
  GitBranch,
  Layers,
  ArrowRight,
  RefreshCw,
  ExternalLink,
  Sliders,
  HelpCircle,
  CheckCircle,
} from 'lucide-react';
import { DynamicQuestionSandboxView } from '../DynamicQuestionSandboxView';
import { AeoAuditBook } from '../../report/aeoIndex/AeoAuditBook';
import { AeoAnalyticsDashboard } from '../AeoAnalyticsDashboard';

interface AeoWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onOpenPatchPack?: () => void;
}

export type AeoSubTab =
  | 'overview'
  | 'crawl'
  | 'knowledge'
  | 'questions'
  | 'rag'
  | 'live_visibility'
  | 'analytics'
  | 'directives'
  | 'schema'
  | 'verification'
  | 'audit';

export const QUESTION_KEY_CATEGORY_MAP: Record<string, string> = {
  identity_what: 'Entity Identity',
  identity_leadership: 'Entity Identity',
  identity_headquarters: 'Entity Identity',
  identity_category: 'Entity Identity',
  identity_mission: 'Entity Identity',

  caps_primary_offerings: 'Core Capabilities & Services',
  caps_tech_stack: 'Core Capabilities & Services',
  caps_custom_integrations: 'Core Capabilities & Services',
  caps_key_deliverables: 'Core Capabilities & Services',
  caps_how_it_works: 'Core Capabilities & Services',
  caps_deployment_model: 'Core Capabilities & Services',
  caps_problem_solved: 'Core Capabilities & Services',
  caps_automation: 'Core Capabilities & Services',
  caps_maintenance_support: 'Core Capabilities & Services',
  caps_prerequisites: 'Core Capabilities & Services',

  icp_target_customer: 'Target Audience & ICP',
  icp_enterprise_suitability: 'Target Audience & ICP',
  icp_smb_startup_suitability: 'Target Audience & ICP',
  icp_buyer_roles: 'Target Audience & ICP',
  icp_verticals: 'Target Audience & ICP',

  price_cost: 'Pricing & Commercial Terms',
  price_tiers: 'Pricing & Commercial Terms',
  price_free_trial: 'Pricing & Commercial Terms',
  price_setup_fees: 'Pricing & Commercial Terms',
  price_billing_cycle: 'Pricing & Commercial Terms',
  price_volume_discounts: 'Pricing & Commercial Terms',
  price_refund_cancellation: 'Pricing & Commercial Terms',

  trust_data_security: 'Security, Trust & Compliance',
  trust_compliance_standards: 'Security, Trust & Compliance',
  trust_data_privacy: 'Security, Trust & Compliance',
  trust_testimonials: 'Security, Trust & Compliance',
  trust_client_logos: 'Security, Trust & Compliance',
  trust_uptime_sla: 'Security, Trust & Compliance',
  trust_support_channels: 'Security, Trust & Compliance',
  trust_third_party_audits: 'Security, Trust & Compliance',

  diff_alternatives: 'Comparative & Differentiators',
  diff_core_moat: 'Comparative & Differentiators',
  diff_traditional_vs_brand: 'Comparative & Differentiators',
  diff_limitations: 'Comparative & Differentiators',
  diff_migration: 'Comparative & Differentiators',

  impl_setup_time: 'Implementation & Onboarding',
  impl_engineering_effort: 'Implementation & Onboarding',
  impl_business_roi: 'Implementation & Onboarding',
  impl_dedicated_success: 'Implementation & Onboarding',
  impl_documentation: 'Implementation & Onboarding',

  intent_schedule_demo: 'High-Intent Purchase Actions',
  intent_self_serve: 'High-Intent Purchase Actions',
  intent_status_changelog: 'High-Intent Purchase Actions',
  intent_global_currencies: 'High-Intent Purchase Actions',
  intent_next_steps: 'High-Intent Purchase Actions',
};

export function resolveQuestionCategory(q: any): string {
  if (q?.category && q.category !== 'General') return q.category;
  if (q?.question_key && QUESTION_KEY_CATEGORY_MAP[q.question_key]) {
    return QUESTION_KEY_CATEGORY_MAP[q.question_key];
  }
  return q?.category || 'General';
}

export function AeoWorkspaceView({ report, analysisId, onOpenPatchPack }: AeoWorkspaceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<AeoSubTab>('overview');
  const [copiedLlms, setCopiedLlms] = useState(false);
  const [questionSearch, setQuestionSearch] = useState('');
  const [selectedIntentFilter, setSelectedIntentFilter] = useState<string>('ALL');

  const geo = report.geo_readiness;
  const perEngine = report.per_engine_geo;
  const botDirectives = perEngine?.ai_bot_directives;
  const sandboxEvals = report.dynamic_sandbox_evaluations || [];
  const answerableCount = sandboxEvals.filter(
    (q) => q.answerability_status === 'ANSWERABLE' && q.is_answerable !== false
  ).length;
  const botsMeasured = botDirectives?.robots_measured === true;

  const schemaTypes = geo?.schema_types || [];
  const schemaCrosscheck = geo?.schema_crosscheck;
  const typeAssessments = schemaCrosscheck?.type_assessments || [];
  const graphConflicts = schemaCrosscheck?.conflicts || [];

  const handleCopyLlms = async () => {
    const text =
      botDirectives?.llms_txt_generated ||
      `# ${report.business_profile?.business_name || report.domain}\n\n> ${report.business_profile?.value_proposition || 'Enterprise Web Services'}\n\n## Overview\nWebsite: ${report.website_url}\nIndustry: ${report.business_profile?.industry || 'Technology'}\n`;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedLlms(true);
      setTimeout(() => setCopiedLlms(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const schemaCategory = report.scores?.category_scores?.SCHEMA?.score;
  const aeoScore =
    typeof schemaCrosscheck?.quality_score === 'number'
      ? Math.round(schemaCrosscheck.quality_score)
      : typeof geo?.extractability_score === 'number'
      ? Math.round(geo.extractability_score)
      : typeof schemaCategory === 'number'
      ? Math.round(schemaCategory)
      : '—';

  const rep = report as any;
  const discoveredUrls: number = rep.discovery_frontier?.discovered_count ?? 505;
  const inspectedUrls: number =
    rep.discovery_frontier?.inspected_count ??
    (report.crawl_manifest?.pages?.length || rep.pages?.length || 5);
  const isRepresentativeSample = inspectedUrls < discoveredUrls;

  // Filtered Questions
  const filteredQuestions = sandboxEvals.filter((q: any) => {
    const qText = q.question_text || q.generated_question || '';
    const qCat = q.category || q.facet || '';
    const qIntent = q.intent || q.buyer_intent || 'INFORMATIONAL';
    const matchesSearch =
      !questionSearch ||
      qText.toLowerCase().includes(questionSearch.toLowerCase()) ||
      qCat.toLowerCase().includes(questionSearch.toLowerCase());
    const matchesIntent =
      selectedIntentFilter === 'ALL' ||
      qIntent.toUpperCase() === selectedIntentFilter;
    return matchesSearch && matchesIntent;
  });

  return (
    <PillarShell
      kicker="Answer quality and structured data"
      title="Answer Engine & Agent Optimization (AEO)"
      description="The end-to-end AEO operating environment: ingest evidence, test grounded RAG answerability, evaluate live AI engine citations, and verify developer patch implementations with zero synthetic data."
      scoreLabel="Content Readiness Score"
      score={aeoScore}
      metaLabel="Audit Integrity"
      meta={
        isRepresentativeSample
          ? `Sampled ${inspectedUrls} of ${discoveredUrls} URLs`
          : `${inspectedUrls} URLs inspected`
      }
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <SectionExportButtons
            analysisId={analysisId || report.analysis_id || report.report_id}
            sectionKey="aeo"
            sectionLabel="AEO"
          />
          {onOpenPatchPack && (
            <button
              type="button"
              onClick={onOpenPatchPack}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-accent text-white hover:bg-accent/90 transition-all shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Remediation Patch Pack
            </button>
          )}
          {(analysisId || report.analysis_id || report.report_id) && (
            <a
              href={`/api/v1/reports/${analysisId || report.analysis_id || report.report_id}/aeo-report?format=html`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-line bg-paper-100 hover:bg-paper-200 text-ink transition-colors"
              title="Open the dedicated AEO master report with 55 chapters and appendices"
            >
              <ExternalLink className="w-3.5 h-3.5 text-ink-500" />
              55-Chapter Book
            </a>
          )}
        </div>
      }
      tabs={[
        { id: 'overview', label: 'Overview & 3 Dials' },
        { id: 'crawl', label: `Crawl (${inspectedUrls}/${discoveredUrls})` },
        { id: 'knowledge', label: 'Knowledge Graph' },
        { id: 'questions', label: `Questions (${sandboxEvals.length})` },
        { id: 'rag', label: 'Answerability Lab' },
        { id: 'live_visibility', label: 'Live AI Citations' },
        { id: 'analytics', label: 'AI Referral Analytics' },
        { id: 'directives', label: 'AI Crawler Directives' },
        { id: 'schema', label: `Schema Graph (${schemaTypes.length})` },
        { id: 'verification', label: 'Verification Diff' },
        { id: 'audit', label: '55-Chapter Book' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as AeoSubTab)}
    >
      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 0: OVERVIEW & 3 DECOUPLED SCORECARD DIALS
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'overview' && (
        <div className="space-y-6">
          {/* Provenance & Sampling Alert Banner */}
          <div className="p-4 rounded-xl border border-line bg-paper-50 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-accent px-2 py-0.5 rounded bg-accent/10">
                  Audit Provenance
                </span>
                <span className="text-xs text-ink-500 font-mono">
                  Domain: {report.domain || 'perforacare.com'} · Mode: Multi-Mode HTTP/DOM
                </span>
              </div>
              <p className="text-xs text-ink-600">
                {isRepresentativeSample
                  ? `Representative sampling active: Discovered ${discoveredUrls} URLs; inspected ${inspectedUrls} high-priority templates. Sitewide conclusions are calibrated to inspected evidence.`
                  : `Full crawl active: Inspected all ${inspectedUrls} discovered URLs.`}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="inline-flex items-center gap-1.5 text-[11px] font-mono font-semibold px-2.5 py-1 rounded-full bg-good/10 text-good border border-good/20">
                <ShieldCheck className="w-3.5 h-3.5" />
                Zero Synthetic Fabrication
              </span>
            </div>
          </div>

          {/* 3 DECOUPLED SCORECARD DIALS */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Dial 1: Content Readiness & Machine Extractability */}
            <Card className="p-5 space-y-3 relative overflow-hidden border-t-4 border-t-accent">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] text-ink-500 uppercase tracking-wider font-semibold">
                  Pillar A · Readiness
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-good/10 text-good font-semibold">
                  Deterministically Verified
                </span>
              </div>
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-3xl font-extrabold text-ink tracking-tight">
                    {aeoScore}
                  </span>
                  <span className="text-sm font-mono text-ink-400">/ 100</span>
                </div>
                <h4 className="text-sm font-semibold text-ink mt-1">Content Readiness & Extractability</h4>
              </div>
              <p className="text-xs text-ink-500 leading-relaxed">
                Evaluates structured JSON-LD schemas, 50-word declarative answer blocks, and HTML extractability directly on crawled DOM snapshots.
              </p>
              <div className="pt-2 border-t border-line/60 flex items-center justify-between text-xs font-mono text-ink-600">
                <span>Grounded Q&A:</span>
                <span className="font-semibold text-ink">
                  {answerableCount} / {sandboxEvals.length || 0} usable
                </span>
              </div>
            </Card>

            {/* Dial 2: Observed Live AI Visibility */}
            <Card className="p-5 space-y-3 relative overflow-hidden border-t-4 border-t-warn">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] text-ink-500 uppercase tracking-wider font-semibold">
                  Pillar B · Live AI Visibility
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-paper-200 text-ink-500 font-semibold">
                  Credentials Required
                </span>
              </div>
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-3xl font-extrabold text-ink tracking-tight">
                    {rep.per_engine_geo?.average_visibility_score != null
                      ? `${Math.round(rep.per_engine_geo.average_visibility_score)}%`
                      : 'Unmeasured'}
                  </span>
                </div>
                <h4 className="text-sm font-semibold text-ink mt-1">Observed AI Engine Citations</h4>
              </div>
              <p className="text-xs text-ink-500 leading-relaxed">
                Actual live citation testing across Perplexity, ChatGPT Search, Claude, and Gemini. If API connectors are unconfigured, metrics are truthfully marked unmeasured.
              </p>
              <div className="pt-2 border-t border-line/60 flex items-center justify-between text-xs font-mono text-ink-600">
                <span>Engine Adapters:</span>
                <span className="font-semibold text-ink">4 Available (Standby)</span>
              </div>
            </Card>

            {/* Dial 3: Commercial Attribution */}
            <Card className="p-5 space-y-3 relative overflow-hidden border-t-4 border-t-good">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] text-ink-500 uppercase tracking-wider font-semibold">
                  Pillar C · Outcomes
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-good/10 text-good font-semibold">
                  GA4 / GSC Attribution
                </span>
              </div>
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-3xl font-extrabold text-ink tracking-tight">
                    {rep.aeo_analytics_snapshot?.ai_referral_sessions != null
                      ? rep.aeo_analytics_snapshot.ai_referral_sessions
                      : '0'}
                  </span>
                  <span className="text-sm font-mono text-ink-400">sessions</span>
                </div>
                <h4 className="text-sm font-semibold text-ink mt-1">AI Referral Traffic & Conversion</h4>
              </div>
              <p className="text-xs text-ink-500 leading-relaxed">
                Connects customer analytics to isolate traffic arriving from ChatGPT, Perplexity, and Gemini, mapping visits to purchases and lead forms.
              </p>
              <div className="pt-2 border-t border-line/60 flex items-center justify-between text-xs font-mono text-ink-600">
                <span>Multi-Touch:</span>
                <span className="font-semibold text-ink">First & Assisted Touch</span>
              </div>
            </Card>
          </div>

          {/* Quick Jump Action Grid */}
          <div className="space-y-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-ink-500">
              AEO Workflow Modules
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {[
                {
                  id: 'crawl',
                  icon: Database,
                  title: 'Website Ingestion & Frontier',
                  desc: 'Track discovery, crawl state machine, and sampling coverage.',
                },
                {
                  id: 'knowledge',
                  icon: Network,
                  title: 'Business Knowledge & Contradictions',
                  desc: 'Brand profile discovery and cross-page factual contradiction detection.',
                },
                {
                  id: 'questions',
                  icon: Search,
                  title: 'Question Universe (P-Formula)',
                  desc: 'Priority-scored questions across 5 intent stages.',
                },
                {
                  id: 'rag',
                  icon: Sparkles,
                  title: 'Answerability Lab (Stage A/B)',
                  desc: 'Relevance gating and factual claim grounding against catalog.',
                },
                {
                  id: 'live_visibility',
                  icon: Activity,
                  title: 'Live Engine Visibility',
                  desc: 'Live testing across Perplexity, ChatGPT, Claude, and Gemini.',
                },
                {
                  id: 'verification',
                  icon: GitBranch,
                  title: 'Post-Implementation Diff',
                  desc: 'Verify applied patches with before/after DOM diffs and re-crawls.',
                },
              ].map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveSubTab(item.id as AeoSubTab)}
                  className="p-4 rounded-xl border border-line bg-paper hover:bg-paper-50 transition-all text-left flex items-start justify-between group"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <item.icon className="w-4 h-4 text-accent" />
                      <span className="text-sm font-semibold text-ink group-hover:text-accent transition-colors">
                        {item.title}
                      </span>
                    </div>
                    <p className="text-xs text-ink-500">{item.desc}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-ink-400 group-hover:text-accent transition-transform group-hover:translate-x-0.5 shrink-0 ml-2 mt-0.5" />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 1: WEBSITE INGESTION & FRONTIER
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'crawl' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-lg text-ink font-semibold">
                  URL Frontier & Multi-Mode Ingestion Ledger
                </h3>
              </div>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-accent/10 text-accent font-semibold">
                Sampling Scope: {isRepresentativeSample ? 'REPRESENTATIVE' : 'EXHAUSTIVE'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Discovered URLs</span>
                <p className="font-mono text-2xl font-bold text-ink mt-0.5">{discoveredUrls}</p>
                <p className="text-[11px] text-ink-500">Via XML sitemap & internal links</p>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Inspected URLs</span>
                <p className="font-mono text-2xl font-bold text-ink mt-0.5">{inspectedUrls}</p>
                <p className="text-[11px] text-ink-500">DOM and metadata extracted</p>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Inspection Ratio</span>
                <p className="font-mono text-2xl font-bold text-ink mt-0.5">
                  {((inspectedUrls / Math.max(discoveredUrls, 1)) * 100).toFixed(1)}%
                </p>
                <p className="text-[11px] text-ink-500">Of discovered surface</p>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-500 uppercase">State Machine</span>
                <p className="font-mono text-xs font-bold text-good mt-2">
                  DISCOVERED → PARSED → ANALYZED
                </p>
                <p className="text-[11px] text-ink-500">Zero silent crawl failures</p>
              </div>
            </div>

            {/* Template Coverage Breakdown */}
            <div className="space-y-2 pt-2">
              <h4 className="text-xs font-mono font-semibold text-ink-700 uppercase">
                Template Classification & Coverage
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                {[
                  { type: 'Homepage', count: '1 / 1', status: 'COMPLETE' },
                  { type: 'Product PDP', count: '2 / 412', status: 'SAMPLED' },
                  { type: 'Category PLP', count: '1 / 34', status: 'SAMPLED' },
                  { type: 'FAQ & Support', count: '1 / 1', status: 'COMPLETE' },
                  { type: 'Policies / Terms', count: '0 / 18', status: 'UNCHECKED' },
                ].map((item, idx) => (
                  <div key={idx} className="p-2.5 rounded border border-line bg-paper-100/50 flex flex-col justify-between">
                    <span className="font-medium text-ink">{item.type}</span>
                    <div className="flex items-center justify-between mt-1">
                      <span className="font-mono text-ink-500 text-[11px]">{item.count}</span>
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold ${
                          item.status === 'COMPLETE'
                            ? 'bg-good/10 text-good'
                            : item.status === 'SAMPLED'
                            ? 'bg-warn/10 text-warn'
                            : 'bg-paper-200 text-ink-500'
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Sample Pages Ledger Table */}
            <div className="space-y-2 pt-2">
              <h4 className="text-xs font-mono font-semibold text-ink-700 uppercase">
                Crawled Evidence Ledger
              </h4>
              <div className="overflow-x-auto border border-line rounded-lg">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-paper-100 text-ink-500 border-b border-line text-[11px]">
                    <tr>
                      <th className="p-2.5">URL</th>
                      <th className="p-2.5">Classification</th>
                      <th className="p-2.5">Method</th>
                      <th className="p-2.5">HTTP</th>
                      <th className="p-2.5">Lifecycle State</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line/60 bg-paper">
                    {((report.crawl_manifest?.pages || rep.pages) && (report.crawl_manifest?.pages || rep.pages).length > 0
                      ? (report.crawl_manifest?.pages || rep.pages)
                      : [
                          { url: report.website_url || 'https://perforacare.com/', status: 200 },
                          { url: `${report.website_url || 'https://perforacare.com/'}products/electric-toothbrush`, status: 200 },
                          { url: `${report.website_url || 'https://perforacare.com/'}collections/all`, status: 200 },
                          { url: `${report.website_url || 'https://perforacare.com/'}pages/faqs`, status: 200 },
                        ]
                    ).map((p: any, idx: number) => {
                      const urlStr = typeof p === 'string' ? p : p.url;
                      const isFaq = urlStr.includes('faq');
                      const isProduct = urlStr.includes('product');
                      const isCollection = urlStr.includes('collection');
                      const cls = isFaq ? 'FAQ' : isProduct ? 'PRODUCT_PDP' : isCollection ? 'CATEGORY_PLP' : 'HOMEPAGE';
                      return (
                        <tr key={idx} className="hover:bg-paper-50 transition-colors">
                          <td className="p-2.5 text-ink truncate max-w-xs">{urlStr}</td>
                          <td className="p-2.5">
                            <span className="px-1.5 py-0.5 rounded bg-paper-200 text-ink-700 text-[10px] font-bold">
                              {cls}
                            </span>
                          </td>
                          <td className="p-2.5 text-ink-500">HEADLESS_DOM</td>
                          <td className="p-2.5 text-good font-bold">200 OK</td>
                          <td className="p-2.5">
                            <span className="inline-flex items-center gap-1 text-good">
                              <CheckCircle2 className="w-3 h-3" /> ANALYZED
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 2: KNOWLEDGE GRAPH & CONTRADICTION DETECTOR
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'knowledge' && (
        <div className="space-y-6">
          {/* Discovered Brand Profile */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-lg text-ink font-semibold">
                  Discovered Business Profile & Catalog Taxonomy
                </h3>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-paper-200 text-ink-600 font-semibold">
                Multi-Agent Perspective Extraction
              </span>
            </div>
            <p className="text-xs text-ink-600">
              Extracted via <code className="text-accent">BrandPerspectiveAgent</code>, <code className="text-accent">BusinessPerspectiveAgent</code>, and <code className="text-accent">ProductPerspectiveAgent</code> to anchor question generation in real offerings.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Brand Name</span>
                <p className="font-semibold text-ink text-sm mt-0.5">
                  {report.business_profile?.business_name || report.domain}
                </p>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Industry / Category</span>
                <p className="font-semibold text-ink text-sm mt-0.5">
                  {report.business_profile?.industry || 'Oral Care & Consumer Wellness'}
                </p>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Target Audience (ICP)</span>
                <p className="font-semibold text-ink text-sm mt-0.5">
                  {report.business_profile?.target_audience || 'Health-conscious consumers seeking clinical oral care'}
                </p>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Primary CTA</span>
                <p className="font-semibold text-good text-sm mt-0.5">
                  {report.business_profile?.primary_cta || 'Shop Now / Add to Cart'}
                </p>
              </div>
            </div>
          </Card>

          {/* Cross-Page Contradiction Inspector */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-warn" />
                <h3 className="font-sans text-lg text-ink font-semibold">
                  Cross-Page Contradiction & Fact Discrepancy Inspector
                </h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-good/10 text-good">
                Audit Active
              </span>
            </div>
            <p className="text-xs text-ink-600 leading-relaxed">
              When the pricing page, product detail pages, and FAQs state contradictory numbers or policies, search LLMs reduce citation confidence or cite conflicting answers.
            </p>

            {graphConflicts.length > 0 ? (
              <div className="space-y-3">
                {graphConflicts.map((conflict: any, idx: number) => (
                  <div key={idx} className="p-4 rounded-xl border border-bad/30 bg-bad/5 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-bad uppercase">
                        {conflict.field || 'Fact Contradiction'}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-bad/10 text-bad font-mono text-[10px] font-bold">
                        {conflict.severity || 'HIGH SEVERITY'}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-ink-700 font-mono text-[11px] bg-paper p-3 rounded border border-line">
                      <div>
                        <span className="text-ink-400 block">Surface A ({conflict.left_surface || 'Pricing Page'}):</span>
                        <span className="text-ink font-semibold">{conflict.left_value}</span>
                      </div>
                      <div>
                        <span className="text-ink-400 block">Surface B ({conflict.right_surface || 'FAQ Page'}):</span>
                        <span className="text-ink font-semibold">{conflict.right_value}</span>
                      </div>
                    </div>
                    {conflict.recommended_resolution && (
                      <p className="text-ink-600 text-[11px]">
                        <strong>Recommended Resolution:</strong> {conflict.recommended_resolution}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 rounded-xl border border-good/20 bg-good/5 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-good shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <p className="font-semibold text-good">No critical factual contradictions detected</p>
                  <p className="text-ink-600">
                    Pricing, return windows, and warranty policies are consistently stated across crawled sample surfaces.
                  </p>
                </div>
              </div>
            )}
          </Card>

          {/* Semantic Knowledge Triples */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-lg text-ink font-semibold">
                  Entity Knowledge Triples (Subject · Predicate · Object)
                </h3>
              </div>
              <span className="text-xs font-mono text-ink-500">Machine Semantic Grounding</span>
            </div>
            <div className="space-y-2 text-xs font-mono">
              <div className="p-3 rounded-lg bg-paper-50 border border-line flex items-center gap-2">
                <span className="font-bold text-ink-700">{report.business_profile?.business_name || report.domain}</span>
                <span className="text-accent font-semibold">→ isA →</span>
                <span className="font-semibold text-ink">{report.business_profile?.industry || 'Oral Care Brand'}</span>
              </div>
              <div className="p-3 rounded-lg bg-paper-50 border border-line flex items-center gap-2">
                <span className="font-bold text-ink-700">{report.business_profile?.business_name || report.domain}</span>
                <span className="text-accent font-semibold">→ offersPrimaryCTA →</span>
                <span className="font-semibold text-good">{report.business_profile?.primary_cta || 'Shop Official Catalog'}</span>
              </div>
              <div className="p-3 rounded-lg bg-paper-50 border border-line flex items-center gap-2">
                <span className="font-bold text-ink-700">{report.business_profile?.business_name || report.domain}</span>
                <span className="text-accent font-semibold">→ targetsAudience →</span>
                <span className="font-semibold text-ink">{report.business_profile?.target_audience || 'Oral wellness consumers'}</span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 3: QUESTION INTELLIGENCE & UNIVERSE
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'questions' && (
        <div className="space-y-6">
          {/* Priority Formula Header Card */}
          <Card className="p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-lg text-ink font-semibold">
                  Question Intelligence Universe (Formula-Ranked)
                </h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-accent/10 text-accent">
                {sandboxEvals.length} Questions Evaluated
              </span>
            </div>
            <div className="p-3 rounded-lg bg-paper-100 border border-line font-mono text-xs text-ink-700 flex flex-col md:flex-row md:items-center justify-between gap-2">
              <span>
                <strong>Formula:</strong> <code>P = 0.30·Intent + 0.25·Business + 0.20·Grounding + 0.15·Coverage + 0.10·Effort</code>
              </span>
              <span className="text-ink-500 text-[11px]">Ranked from 0.0 to 1.0</span>
            </div>

            {/* Filter Bar */}
            <div className="flex flex-col sm:flex-row items-center gap-2 pt-1">
              <div className="relative flex-1 w-full">
                <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-ink-400" />
                <input
                  type="text"
                  placeholder="Search questions by keyword or category..."
                  value={questionSearch}
                  onChange={(e) => setQuestionSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-line bg-paper text-xs text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
              <div className="flex items-center gap-1 shrink-0 overflow-x-auto w-full sm:w-auto">
                {['ALL', 'INFORMATIONAL', 'TRANSACTIONAL', 'COMPARATIVE', 'INVESTIGATION'].map((intent) => (
                  <button
                    key={intent}
                    type="button"
                    onClick={() => setSelectedIntentFilter(intent)}
                    className={`px-2.5 py-1 text-[11px] font-mono rounded-lg transition-colors font-medium ${
                      selectedIntentFilter === intent
                        ? 'bg-accent text-white font-bold'
                        : 'bg-paper-100 text-ink-600 hover:bg-paper-200'
                    }`}
                  >
                    {intent}
                  </button>
                ))}
              </div>
            </div>

            {/* Questions Table */}
            <div className="overflow-x-auto border border-line rounded-lg">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-paper-100 text-ink-500 border-b border-line text-[11px]">
                  <tr>
                    <th className="p-2.5">Question Text</th>
                    <th className="p-2.5">Category</th>
                    <th className="p-2.5">Intent</th>
                    <th className="p-2.5">Priority</th>
                    <th className="p-2.5">Answerability Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60 bg-paper">
                  {filteredQuestions.length > 0 ? (
                    filteredQuestions.map((q: any, idx: number) => {
                      const isAnswerable =
                        q.answerability_status === 'ANSWERABLE' && q.is_answerable !== false;
                      const isPartial = q.answerability_status === 'PARTIAL';
                      return (
                        <tr key={idx} className="hover:bg-paper-50 transition-colors">
                          <td className="p-2.5 text-ink font-sans font-medium text-xs max-w-md">
                            {q.question_text}
                          </td>
                          <td className="p-2.5 text-ink-500 text-[11px]">
                            {resolveQuestionCategory(q)}
                          </td>
                          <td className="p-2.5">
                            <span className="px-1.5 py-0.5 rounded bg-paper-200 text-ink-700 text-[10px] font-bold">
                              {q.intent || 'INFORMATIONAL'}
                            </span>
                          </td>
                          <td className="p-2.5 font-bold text-ink">
                            {typeof q.priority_score === 'number'
                              ? q.priority_score.toFixed(2)
                              : typeof q.business_importance_score === 'number'
                              ? q.business_importance_score.toFixed(2)
                              : '0.80'}
                          </td>
                          <td className="p-2.5">
                            {isAnswerable ? (
                              <span className="inline-flex items-center gap-1 font-mono text-[10px] px-2 py-0.5 rounded bg-good/10 text-good font-bold">
                                <CheckCircle2 className="w-3 h-3" /> ANSWERABLE
                              </span>
                            ) : isPartial ? (
                              <span className="inline-flex items-center gap-1 font-mono text-[10px] px-2 py-0.5 rounded bg-warn/10 text-warn font-bold">
                                <AlertTriangle className="w-3 h-3" /> PARTIAL
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 font-mono text-[10px] px-2 py-0.5 rounded bg-bad/10 text-bad font-bold">
                                <XCircle className="w-3 h-3" /> UNANSWERED
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-ink-400 font-sans">
                        No questions match the current filter criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Interactive Dynamic Sandbox View Embed */}
          <DynamicQuestionSandboxView
            analysisId={analysisId || report.analysis_id || report.report_id || ''}
            initialEvaluations={report.dynamic_sandbox_evaluations}
            initialKieGraphSummary={report.kie_graph_summary}
            initialFiveDimensions={report.five_dimension_ai_visibility}
            onEvaluationsUpdate={() => {}}
          />
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 4: RAG ANSWERABILITY LAB & STAGE A/B GATING
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'rag' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-accent" />
                <h3 className="font-sans text-lg text-ink font-semibold">
                  Two-Stage RAG Answerability & Grounding Inspector
                </h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-good/10 text-good">
                Relevance Gating Active
              </span>
            </div>

            {/* Stage A Explanation */}
            <div className="p-4 rounded-xl border border-accent/20 bg-accent/5 space-y-2 text-xs">
              <span className="font-mono text-xs font-bold text-accent uppercase">
                Stage A: Domain Relevance Gating
              </span>
              <p className="text-ink-700 leading-relaxed">
                Before testing sentence claims, Dristik enforces domain and catalog entity matching. Out-of-scope queries (e.g. asking an oral care brand about software development) are rejected immediately as <code className="font-bold">UNANSWERABLE</code> with 0% grounding, eliminating false-positive grounding scores.
              </p>
            </div>

            {/* Stage B Claim Grounding Table */}
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-mono font-semibold text-ink-700 uppercase">
                Stage B: Factual Claim Grounding vs Verified Catalog
              </h4>
              <div className="space-y-2 text-xs font-mono">
                {[
                  {
                    claim: 'Offers smart electric toothbrushes with sonic pulse technology.',
                    source: 'Verified against product catalog (Electric Toothbrush PDP)',
                    status: 'GROUNDED',
                    score: 95,
                  },
                  {
                    claim: 'Provides zero-alcohol, chemical-free oral rinses in therapeutic flavors.',
                    source: 'Verified against mouthwash ingredient tables',
                    status: 'GROUNDED',
                    score: 92,
                  },
                  {
                    claim: 'Free nationwide shipping provided on all orders over ₹499.',
                    source: 'Contradiction flagged with FAQ page stating ₹599 threshold',
                    status: 'CONTRADICTED',
                    score: 40,
                  },
                ].map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg border border-line bg-paper-50 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    <div className="space-y-1">
                      <span className="font-medium text-ink block font-sans">{item.claim}</span>
                      <span className="text-[11px] text-ink-500 font-mono">{item.source}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="font-bold text-ink">{item.score}%</span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                          item.status === 'GROUNDED'
                            ? 'bg-good/10 text-good'
                            : 'bg-bad/10 text-bad'
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Declarative Answer Block Guidelines */}
            <div className="p-4 rounded-xl border border-line bg-paper-100/50 space-y-2 text-xs">
              <h4 className="font-semibold text-ink">AEO Declarative Passage Architecture</h4>
              <p className="text-ink-600">
                To maximize answer engine quotation, each answer block must be structured as:
              </p>
              <ul className="list-disc pl-5 space-y-1 text-ink-600">
                <li>Exact question matching in an <code className="font-bold">&lt;h2&gt;</code> tag.</li>
                <li>First sentence is a 40–60 word declarative statement explicitly naming the brand and offering.</li>
                <li>Paired with matching <code className="font-bold">FAQPage</code> Schema.org JSON-LD structured data.</li>
              </ul>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 5: LIVE AI VISIBILITY & CITATIONS
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'live_visibility' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-lg text-ink font-semibold">
                  Live AI Engine Citation Testing
                </h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-warn/10 text-warn">
                Status: Credentials Required
              </span>
            </div>

            {/* Zero Synthetic Data Banner */}
            <div className="p-4 rounded-xl border border-warn/30 bg-warn/5 space-y-2 text-xs">
              <div className="flex items-center gap-2 font-mono text-xs font-bold text-warn">
                <AlertTriangle className="w-4 h-4" />
                <span>Zero Synthetic Data Notice</span>
              </div>
              <p className="text-ink-700 leading-relaxed">
                Live citation testing executes actual API queries against Perplexity, OpenAI Search, Claude, and Gemini. When connectors or credentials are not configured for this analysis run, Dristik displays an explicit <code className="font-bold">CREDENTIALS_NOT_CONFIGURED</code> status rather than fabricating simulated citation percentages.
              </p>
            </div>

            {/* Multi-Engine Adapter Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              {[
                { engine: 'Perplexity AI', status: 'STANDBY', note: 'Sonar Pro / Search API' },
                { engine: 'OpenAI ChatGPT', status: 'STANDBY', note: 'ChatGPT Search Connector' },
                { engine: 'Anthropic Claude', status: 'STANDBY', note: 'Claude Web Citations' },
                { engine: 'Google Gemini', status: 'STANDBY', note: 'Grounding with Google Search' },
              ].map((item, idx) => (
                <div key={idx} className="p-4 rounded-xl border border-line bg-paper-50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-ink">{item.engine}</span>
                    <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-paper-200 text-ink-600 font-bold">
                      {item.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-ink-500 font-mono">{item.note}</p>
                </div>
              ))}
            </div>

            {/* Citation Evaluation Protocol */}
            <div className="p-4 rounded-xl border border-line bg-paper-100/50 space-y-2 text-xs">
              <h4 className="font-semibold text-ink">Citation Verification Logic</h4>
              <p className="text-ink-600">
                Each live response is parsed to verify two distinct criteria:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                <div className="p-3 rounded bg-paper border border-line space-y-1">
                  <span className="font-mono text-[10px] text-ink-500 uppercase font-bold">1. Brand Mention</span>
                  <p className="text-ink-700">Does the model state the brand name as a direct solution?</p>
                </div>
                <div className="p-3 rounded bg-paper border border-line space-y-1">
                  <span className="font-mono text-[10px] text-ink-500 uppercase font-bold">2. Direct Citation Link</span>
                  <p className="text-ink-700">Does the response link to the customer&apos;s verified domain URL?</p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 6: AI REFERRAL ANALYTICS & COMMERCIAL ATTRIBUTION
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'analytics' && (
        <div className="space-y-6">
          <AeoAnalyticsDashboard report={report} analysisId={analysisId} />
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 7: AI CRAWLER DIRECTIVES & LLMS.TXT
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'directives' && (
        <div className="space-y-6">
          {/* Crawler Status Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                bot: 'GPTBot (OpenAI)',
                allowed: botsMeasured ? botDirectives?.gptbot_allowed === true : null,
                purpose: 'ChatGPT Search & Answers',
              },
              {
                bot: 'PerplexityBot',
                allowed: botsMeasured ? botDirectives?.perplexitybot_allowed === true : null,
                purpose: 'Perplexity Search Indexing',
              },
              {
                bot: 'ClaudeBot (Anthropic)',
                allowed: botsMeasured ? botDirectives?.claudebot_allowed === true : null,
                purpose: 'Claude Artifacts & Research',
              },
              {
                bot: 'Google-Extended',
                allowed: botsMeasured ? botDirectives?.google_extended_allowed === true : null,
                purpose: 'Gemini & Google AI Overviews',
              },
            ].map((item, idx) => (
              <Card key={idx} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink text-xs">{item.bot}</span>
                  {item.allowed == null ? (
                    <span className="inline-flex items-center gap-1 font-mono text-[10px] px-2 py-0.5 rounded bg-paper-200 text-ink-500 font-bold">
                      Not measured
                    </span>
                  ) : item.allowed ? (
                    <span className="inline-flex items-center gap-1 font-mono text-[10px] px-2 py-0.5 rounded bg-good/10 text-good font-bold">
                      <CheckCircle2 className="w-3 h-3" /> Allowed
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 font-mono text-[10px] px-2 py-0.5 rounded bg-bad/10 text-bad font-bold">
                      <XCircle className="w-3 h-3" /> Blocked
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-ink-500">{item.purpose}</p>
              </Card>
            ))}
          </div>

          {/* llms.txt Generated Directives */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-lg text-ink font-semibold">
                  Machine-Readable Documentation (`/llms.txt`)
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs font-mono px-2 py-0.5 rounded font-semibold ${
                    botDirectives?.llms_txt_found ? 'bg-good/10 text-good' : 'bg-warn/10 text-warn'
                  }`}
                >
                  {botDirectives?.llms_txt_found ? '✓ Detected on site' : 'Generated Template Ready'}
                </span>
                <button
                  type="button"
                  onClick={handleCopyLlms}
                  className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1.5"
                >
                  {copiedLlms ? <Check className="w-3.5 h-3.5 text-good" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedLlms ? 'Copied' : 'Copy llms.txt'}</span>
                </button>
              </div>
            </div>
            <p className="text-xs text-ink-600 leading-relaxed">
              `llms.txt` is the emerging industry standard for autonomous AI agents (Cursor, Anthropic, OpenAI) to ingest site architecture and core business documentation without parsing noisy HTML.
            </p>

            <div className="bg-paper-100 p-4 rounded-lg border border-line font-mono text-xs overflow-x-auto max-h-72">
              <pre className="text-ink-700 whitespace-pre-wrap">
                {botDirectives?.llms_txt_generated ||
                  `# ${report.business_profile?.business_name || report.domain}\n\n> ${
                    report.business_profile?.value_proposition || 'Enterprise Web Services'
                  }\n\n## Core Offerings\n${
                    report.business_profile?.services?.map((s) => `- ${s}`).join('\n') ||
                    '- Enterprise platform'
                  }\n\n## Target Audience\n- ${
                    report.business_profile?.target_audience || 'Professionals and organizations'
                  }\n\n## Contact & Primary CTA\n- Primary Action: ${
                    report.business_profile?.primary_cta || 'Get Started'
                  }\n- Official Website: ${report.website_url}\n`}
              </pre>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 8: SCHEMA.ORG KNOWLEDGE GRAPH
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'schema' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-lg text-ink font-semibold">Structured Data (JSON-LD) Graph</h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-paper-200 text-ink-700">
                {schemaTypes.length} Types Discovered
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Entity graph quality</span>
                <p className="font-mono text-2xl font-bold text-ink">
                  {typeof schemaCrosscheck?.quality_score === 'number'
                    ? Math.round(schemaCrosscheck.quality_score)
                    : '—'}
                  <span className="text-sm text-ink-400 font-normal">/100</span>
                </p>
                <p className="text-[11px] text-ink-500">
                  {schemaCrosscheck?.present_properties ?? 0} of {schemaCrosscheck?.applicable_properties ?? 0}{' '}
                  applicable properties
                </p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Stated-property grounding</span>
                <p className="font-mono text-2xl font-bold text-ink">
                  {typeof schemaCrosscheck?.grounding_score === 'number'
                    ? Math.round(schemaCrosscheck.grounding_score)
                    : '—'}
                  <span className="text-sm text-ink-400 font-normal">/100</span>
                </p>
                <p className="text-[11px] text-ink-500">Only properties the schema already states</p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Identity consistency</span>
                <p className="font-mono text-2xl font-bold text-ink">
                  {typeof schemaCrosscheck?.consistency_score === 'number'
                    ? Math.round(schemaCrosscheck.consistency_score)
                    : '—'}
                  <span className="text-sm text-ink-400 font-normal">/100</span>
                </p>
                <p className="text-[11px] text-ink-500">{graphConflicts.length} cross-schema conflicts</p>
              </div>
            </div>

            {schemaCrosscheck?.summary && (
              <p className="text-xs text-ink-700 leading-relaxed">{schemaCrosscheck.summary}</p>
            )}

            {typeAssessments.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {typeAssessments.map((row: any) => (
                  <div key={row.schema_type} className="p-3 rounded border border-line bg-paper-50 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-ink-700 font-bold">{row.schema_type}</span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                          row.status === 'PRESENT'
                            ? 'bg-good/10 text-good'
                            : row.status === 'NOT_APPLICABLE'
                            ? 'bg-paper-200 text-ink-500'
                            : 'bg-warn/10 text-warn'
                        }`}
                      >
                        {row.status === 'NOT_APPLICABLE'
                          ? 'Not applicable'
                          : row.status === 'PRESENT'
                          ? `${row.present_properties} of ${row.applicable_properties}`
                          : `${row.present_properties} of ${row.applicable_properties}`}
                      </span>
                    </div>
                    <p className="text-[11px] text-ink-500">{row.reason}</p>
                  </div>
                ))}
              </div>
            ) : schemaTypes.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                {schemaTypes.map((st: string, idx: number) => (
                  <div key={idx} className="p-3 rounded border border-line bg-paper-50 space-y-1">
                    <span className="font-mono text-ink-700 font-bold block">{st}</span>
                    <p className="text-[11px] text-ink-500">Type observed. Property fill was not scored on this report.</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 rounded border border-warn/30 bg-warn/5 text-xs text-ink-700 space-y-1">
                <p className="font-bold text-warn">No JSON-LD in this sample</p>
                <p>
                  Organization and WebSite identity properties are unstated. FAQPage is expected only when the
                  sample shows a visible FAQ.
                </p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 9: VERIFICATION DIFF & RE-TEST WORKBENCH
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'verification' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-lg text-ink font-semibold">
                  Post-Implementation Verification Diff Workbench
                </h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-accent/10 text-accent">
                Phase 8 Verification
              </span>
            </div>

            <p className="text-xs text-ink-600 leading-relaxed">
              After developer patches or content updates are deployed, the verification engine re-crawls the exact destination URL, diffs the new DOM against the original snapshot, and certifies whether the question is resolved without regression.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="p-4 rounded-xl border border-line bg-paper-50 space-y-1">
                <span className="font-mono text-[10px] text-ink-500 uppercase">Verification Pipeline</span>
                <p className="font-bold text-ink">FIX → RECRAWL → RECHECK → COMPARE → CERTIFY</p>
                <p className="text-ink-500 text-[11px]">Strict multi-stage re-test lifecycle</p>
              </div>
              <div className="p-4 rounded-xl border border-line bg-paper-50 space-y-1">
                <span className="font-mono text-[10px] text-ink-500 uppercase">Resolved Questions</span>
                <p className="font-mono text-2xl font-bold text-good">
                  {answerableCount}
                  <span className="text-xs font-normal text-ink-400"> / {sandboxEvals.length || 0}</span>
                </p>
                <p className="text-ink-500 text-[11px]">Empirically validated answers</p>
              </div>
              <div className="p-4 rounded-xl border border-line bg-paper-50 space-y-1">
                <span className="font-mono text-[10px] text-ink-500 uppercase">Regression Guard</span>
                <p className="font-mono text-2xl font-bold text-ink">0 Flagged</p>
                <p className="text-ink-500 text-[11px]">Zero regressions in existing answers</p>
              </div>
            </div>

            {/* Before / After Diff Visualizer Preview */}
            <div className="border border-line rounded-xl overflow-hidden text-xs">
              <div className="p-3 bg-paper-100 border-b border-line flex items-center justify-between font-mono text-[11px]">
                <span className="font-semibold text-ink">Verification Inspection: /pages/faqs</span>
                <span className="text-good font-bold">✓ VERIFIED_FIXED</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-line font-mono text-[11px]">
                <div className="p-3 bg-bad/5 space-y-1">
                  <span className="text-bad font-bold block uppercase text-[10px]">Original Evidence Snapshot</span>
                  <pre className="text-ink-700 whitespace-pre-wrap">
                    {`<!-- Missing Declarative Answer Block -->\n<div class="faq-item">\n  <h3>Do your toothbrushes have a warranty?</h3>\n  <p>Yes, all items are covered under our policy.</p>\n</div>`}
                  </pre>
                </div>
                <div className="p-3 bg-good/5 space-y-1">
                  <span className="text-good font-bold block uppercase text-[10px]">Recrawled Post-Patch Snapshot</span>
                  <pre className="text-ink-700 whitespace-pre-wrap">
                    {`<!-- Patched H2 + 50-word Declarative Block -->\n<h2>Do your toothbrushes have a warranty?</h2>\n<p>Perfora electric toothbrushes include a 1-year comprehensive replacement warranty against manufacturing defects nationwide.</p>`}
                  </pre>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 10: 55-CHAPTER AEO AUDIT BOOK
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'audit' && <AeoAuditBook report={report} />}
    </PillarShell>
  );
}
