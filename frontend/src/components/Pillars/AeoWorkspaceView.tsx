import React, { useState } from 'react';
import { ExecutiveReport } from '../../types';
import { PillarShell, Card } from '../ui';
import {
  Bot,
  FileCode,
  HelpCircle,
  Network,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

interface AeoWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onOpenPatchPack?: () => void;
}

type AeoSubTab = 'directives' | 'schema' | 'questions' | 'triples';

export function AeoWorkspaceView({ report, onOpenPatchPack }: AeoWorkspaceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<AeoSubTab>('directives');
  const [selectedQuestionCategory, setSelectedQuestionCategory] = useState<string>('All');
  const [copiedLlms, setCopiedLlms] = useState(false);

  const geo = report.geo_readiness;
  const perEngine = report.per_engine_geo;
  const botDirectives = perEngine?.ai_bot_directives;
  const qGraph = geo?.question_graph_50;
  const questionItems = qGraph?.questions || geo?.questions || [];

  const rawCategories: string[] = Array.from(
    new Set<string>(questionItems.map((q: any) => String(q.category || 'General')))
  );
  const categories: string[] = ['All', ...rawCategories];

  const filteredQuestions = selectedQuestionCategory === 'All'
    ? questionItems
    : questionItems.filter((q: any) => (q.category || 'General') === selectedQuestionCategory);

  const schemaTypes = geo?.schema_types || [];
  const schemaCrosscheck = geo?.schema_crosscheck;
  const typeAssessments = schemaCrosscheck?.type_assessments || [];
  const graphConflicts = schemaCrosscheck?.conflicts || [];

  const handleCopyLlms = async () => {
    const text = botDirectives?.llms_txt_generated || `# ${report.business_profile?.business_name || report.domain}\n\n> ${report.business_profile?.value_proposition || 'Enterprise Web Services'}\n\n## Overview\nWebsite: ${report.website_url}\nIndustry: ${report.business_profile?.industry || 'Technology'}\n`;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedLlms(true);
      setTimeout(() => setCopiedLlms(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const schemaCategory = report.scores?.category_scores?.SCHEMA?.score;
  const aeoScore = typeof schemaCrosscheck?.quality_score === 'number'
    ? Math.round(schemaCrosscheck.quality_score)
    : typeof geo?.extractability_score === 'number'
      ? Math.round(geo.extractability_score)
      : typeof schemaCategory === 'number'
        ? Math.round(schemaCategory)
        : '—';

  return (
    <PillarShell
      kicker="Discipline 3 · Answer Engine & Agent Optimization"
      title="Answer Engine & Agent Optimization (AEO)"
      description="Deterministic on-page machine extractability, JSON-LD structured data graphs, AI bot permissions, and llms.txt directives."
      scoreLabel="AEO Score"
      score={aeoScore}
      metaLabel="Q&A Answers"
      meta={`${qGraph?.supported_count ?? geo?.questions_supported ?? '—'} / ${qGraph?.total_questions ?? geo?.questions_total ?? '50'}`}
      tabs={[
        { id: 'directives', label: 'AI Bots & llms.txt' },
        { id: 'schema', label: `Schema Graph (${schemaTypes.length})` },
        { id: 'questions', label: `50-Question Graph (${questionItems.length})` },
        { id: 'triples', label: 'Entity Triples & Grounding' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as AeoSubTab)}
    >
      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 1: AI BOTS & LLMS.TXT DIRECTIVES
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'directives' && (
        <div className="space-y-6">
          {/* Crawler Status Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                bot: 'GPTBot (OpenAI)',
                allowed: botDirectives?.gptbot_allowed ?? true,
                purpose: 'ChatGPT Search & Answers',
              },
              {
                bot: 'PerplexityBot',
                allowed: botDirectives?.perplexitybot_allowed ?? true,
                purpose: 'Perplexity Search Indexing',
              },
              {
                bot: 'ClaudeBot (Anthropic)',
                allowed: botDirectives?.claudebot_allowed ?? true,
                purpose: 'Claude Artifacts & Research',
              },
              {
                bot: 'Google-Extended',
                allowed: botDirectives?.google_extended_allowed ?? true,
                purpose: 'Gemini & Google AI Overviews',
              },
            ].map((item, idx) => (
              <Card key={idx} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink text-xs">{item.bot}</span>
                  {item.allowed ? (
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
                <FileCode className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  Machine-Readable Documentation (`/llms.txt`)
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-mono px-2 py-0.5 rounded font-semibold ${
                  botDirectives?.llms_txt_found ? 'bg-good/10 text-good' : 'bg-warn/10 text-warn'
                }`}>
                  {botDirectives?.llms_txt_found ? '✓ Detected on site' : '⚡ Generated Template Ready'}
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
              <pre className="text-ink-800 whitespace-pre-wrap">
                {botDirectives?.llms_txt_generated || `# ${report.business_profile?.business_name || report.domain}\n\n> ${report.business_profile?.value_proposition || 'Enterprise Web Services'}\n\n## Core Offerings\n${report.business_profile?.services?.map(s => `- ${s}`).join('\n') || '- Enterprise platform'}\n\n## Target Audience\n- ${report.business_profile?.target_audience || 'Professionals and organizations'}\n\n## Contact & Primary CTA\n- Primary Action: ${report.business_profile?.primary_cta || 'Get Started'}\n- Official Website: ${report.website_url}\n`}
              </pre>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 2: SCHEMA.ORG KNOWLEDGE GRAPH
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'schema' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">Structured Data (JSON-LD) Graph</h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-pine/10 text-pine">
                {schemaTypes.length} Types Discovered
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Entity graph quality</span>
                <p className="font-mono text-2xl font-bold text-ink">
                  {typeof schemaCrosscheck?.quality_score === 'number' ? Math.round(schemaCrosscheck.quality_score) : '—'}
                  <span className="text-sm text-ink-400 font-normal">/100</span>
                </p>
                <p className="text-[11px] text-ink-500">
                  {schemaCrosscheck?.present_properties ?? 0} of {schemaCrosscheck?.applicable_properties ?? 0} applicable properties
                </p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Stated-property grounding</span>
                <p className="font-mono text-2xl font-bold text-ink">
                  {typeof schemaCrosscheck?.grounding_score === 'number' ? Math.round(schemaCrosscheck.grounding_score) : '—'}
                  <span className="text-sm text-ink-400 font-normal">/100</span>
                </p>
                <p className="text-[11px] text-ink-500">Only properties the schema already states</p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-500 uppercase">Identity consistency</span>
                <p className="font-mono text-2xl font-bold text-ink">
                  {typeof schemaCrosscheck?.consistency_score === 'number' ? Math.round(schemaCrosscheck.consistency_score) : '—'}
                  <span className="text-sm text-ink-400 font-normal">/100</span>
                </p>
                <p className="text-[11px] text-ink-500">{graphConflicts.length} cross-schema conflicts</p>
              </div>
            </div>

            {schemaCrosscheck?.summary && (
              <p className="text-xs text-ink-700 leading-relaxed">{schemaCrosscheck.summary}</p>
            )}

            {graphConflicts.length > 0 && (
              <div className="space-y-2">
                {graphConflicts.map((conflict: any, idx: number) => (
                  <div key={idx} className="p-3 rounded border border-bad/30 bg-bad/5 text-xs text-ink-800">
                    <span className="font-mono text-[10px] font-bold text-bad uppercase">{conflict.severity} {conflict.field}</span>
                    <p className="mt-1">
                      {conflict.left_surface} says {conflict.left_value}. {conflict.right_surface} says {conflict.right_value}.
                    </p>
                  </div>
                ))}
              </div>
            )}

            {typeAssessments.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {typeAssessments.map((row: any) => (
                  <div key={row.schema_type} className="p-3 rounded border border-line bg-paper-50 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-pine font-bold">{row.schema_type}</span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                        row.status === 'PRESENT' ? 'bg-good/10 text-good' :
                        row.status === 'NOT_APPLICABLE' ? 'bg-paper-200 text-ink-500' :
                        row.status === 'PARTIAL' ? 'bg-amber-100 text-amber-800' : 'bg-warn/10 text-warn'
                      }`}>
                        {row.status === 'NOT_APPLICABLE' ? 'Not applicable' : row.status === 'PRESENT' ? `${row.present_properties} of ${row.applicable_properties}` : row.status === 'PARTIAL' ? `${row.present_properties} of ${row.applicable_properties}` : 'Absent'}
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
                    <span className="font-mono text-pine font-bold block">{st}</span>
                    <p className="text-[11px] text-ink-500">Type observed. Property fill was not scored on this report.</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 rounded border border-warn/30 bg-warn/5 text-xs text-ink-700 space-y-1">
                <p className="font-bold text-warn">No JSON-LD in this sample</p>
                <p>Organization and WebSite identity properties are unstated. FAQPage is expected only when the sample shows a visible FAQ.</p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 3: 50-QUESTION DETERMINISTIC GRAPH
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'questions' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-serif text-lg text-ink font-semibold">50-Question Extraction Graph</h3>
              <p className="text-xs text-ink-500">
                Deterministic questions tested against on-page content to verify what LLM agents can factually answer.
              </p>
            </div>

            {/* Category Filter */}
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              {categories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setSelectedQuestionCategory(cat)}
                  className={`px-2.5 py-1 rounded font-medium transition-colors ${
                    selectedQuestionCategory === cat
                      ? 'bg-pine text-paper-100 font-bold'
                      : 'bg-paper-100 text-ink-600 hover:bg-paper-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            {filteredQuestions.map((q: any, idx: number) => {
              const supported = q.supported ?? (q.answer_confidence ? q.answer_confidence > 0.5 : true);
              return (
                <Card key={idx} className="p-4 space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-paper-200 text-ink-600">
                          {q.category || 'General'}
                        </span>
                        <span className={`text-[10px] font-mono px-2 py-0.2 rounded font-bold ${
                          supported ? 'bg-good/10 text-good' : 'bg-warn/10 text-warn'
                        }`}>
                          {supported ? '✓ Supported Answer' : '✗ Unanswered On-Page'}
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-ink">{q.question}</h4>
                    </div>
                  </div>

                  {q.answer_snippet && (
                    <div className="p-2.5 rounded bg-paper-50 border border-line text-xs font-mono text-ink-800">
                      <span className="text-pine font-bold">Answer Excerpt: </span>
                      {q.answer_snippet}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 4: ENTITY TRIPLES & GROUNDING
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'triples' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  Entity Knowledge Triples (Subject · Predicate · Object)
                </h3>
              </div>
              <span className="text-xs font-mono text-ink-500">Semantic Grounding</span>
            </div>
            <p className="text-xs text-ink-600">
              Knowledge graphs represent facts about your business as unambiguous triples. This ensures AI models don&apos;t hallucinate services or capabilities you don&apos;t offer.
            </p>

            <div className="space-y-2 text-xs font-mono">
              <div className="p-3 rounded bg-paper-50 border border-line flex items-center gap-2">
                <span className="font-bold text-pine">{report.business_profile?.business_name || report.domain}</span>
                <span className="text-ink-400">→ isA →</span>
                <span className="font-semibold text-ink">{report.business_profile?.industry || 'Enterprise Service'}</span>
              </div>
              <div className="p-3 rounded bg-paper-50 border border-line flex items-center gap-2">
                <span className="font-bold text-pine">{report.business_profile?.business_name || report.domain}</span>
                <span className="text-ink-400">→ offersPrimaryCTA →</span>
                <span className="font-semibold text-good">{report.business_profile?.primary_cta || 'Contact / Get Started'}</span>
              </div>
              <div className="p-3 rounded bg-paper-50 border border-line flex items-center gap-2">
                <span className="font-bold text-pine">{report.business_profile?.business_name || report.domain}</span>
                <span className="text-ink-400">→ targetsAudience →</span>
                <span className="font-semibold text-ink">{report.business_profile?.target_audience || 'Commercial buyers'}</span>
              </div>
            </div>
          </Card>
        </div>
      )}
    </PillarShell>
  );
}
