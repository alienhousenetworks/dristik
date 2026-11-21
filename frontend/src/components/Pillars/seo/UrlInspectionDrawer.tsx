import React, { useState } from 'react';
import { Badge, Button } from '../../ui';
import { ExecutiveReport, Finding } from '../../../types';
import { Check, ChevronRight, Copy, ExternalLink, X } from 'lucide-react';

interface UrlInspectionDrawerProps {
  page: Record<string, any> | null;
  report: ExecutiveReport;
  allPages?: Array<Record<string, any>>;
  onClose: () => void;
  onSelectFinding?: (f: Finding) => void;
}

export type UrlDetailTab =
  | 'overview'
  | 'technical'
  | 'metadata'
  | 'content'
  | 'headings'
  | 'links'
  | 'images'
  | 'schema'
  | 'performance'
  | 'evidence'
  | 'findings'
  | 'history';

export function UrlInspectionDrawer({
  page,
  report,
  allPages = [],
  onClose,
  onSelectFinding,
}: UrlInspectionDrawerProps) {
  const [activeTab, setActiveTab] = useState<UrlDetailTab>('overview');
  const [copied, setCopied] = useState(false);
  const [domViewMode, setDomViewMode] = useState<'rendered' | 'raw' | 'screenshot'>('rendered');
  const [compareUrl, setCompareUrl] = useState<string>('');

  if (!page) return null;

  const url = String(page.url || '');
  const title = String(page.title || '');
  const metaDesc = String(page.meta_description || '');
  const statusCode = page.status_code != null ? Number(page.status_code) : null;
  const canonical = String(page.canonical_url || '');
  const isCanonicalMatch = canonical ? canonical.replace(/\/$/, '') === url.replace(/\/$/, '') : false;
  const h1s: string[] = Array.isArray(page.h1) ? page.h1 : page.h1 ? [String(page.h1)] : [];
  const h2s: string[] = Array.isArray(page.h2) ? page.h2 : [];
  const h3s: string[] = Array.isArray(page.h3) ? page.h3 : [];
  const schemas: string[] = Array.isArray(page.schema_types) ? page.schema_types : [];
  const wordCount = Number(page.word_count ?? 0);
  const outlinks = Array.isArray(page.internal_links) ? page.internal_links : [];
  const externalLinks = Array.isArray(page.external_links) ? page.external_links : [];
  const images = Array.isArray(page.images) ? page.images : [];
  const inlinks = Array.isArray(page.inbound_links) ? page.inbound_links : [];
  const ttfbMs = typeof page.ttfb_ms === 'number' ? page.ttfb_ms : typeof page.ux?.ttfb_ms === 'number' ? page.ux.ttfb_ms : null;
  const lcpMs = typeof page.ux?.lcp_ms === 'number' ? page.ux.lcp_ms : typeof page.lcp_ms === 'number' ? page.lcp_ms : null;
  const clsVal = typeof page.ux?.cls === 'number' ? page.ux.cls : typeof page.cls === 'number' ? page.cls : null;
  const inpMs = typeof page.ux?.inp_ms === 'number' ? page.ux.inp_ms : typeof page.inp_ms === 'number' ? page.inp_ms : null;
  const clickDepth = typeof page.click_depth === 'number' ? page.click_depth : null;
  const robotsMeta = String(page.robots_meta || '').trim() || 'Not specified in head';
  const language = String(page.language || page.html_lang || '').trim() || 'Not declared';
  const rawHtml = String(page.raw_html || '');
  const renderedHtml = String(page.rendered_html || '');
  const screenshotUrl = String(page.screenshot_url || page.screenshot_path || '');

  const pageFindings = (report.findings || []).filter((f) => {
    const affected = (f as any).affected_urls;
    return (Array.isArray(affected) && affected.includes(url)) || (f as any).url === url;
  });

  const comparedPage = allPages.find((p) => String(p.url) === compareUrl) || null;

  const handleCopyUrl = () => {
    navigator.clipboard?.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const tabs: Array<{ id: UrlDetailTab; label: string; count?: number }> = [
    { id: 'overview', label: 'Overview' },
    { id: 'technical', label: 'Technical' },
    { id: 'metadata', label: 'Metadata' },
    { id: 'content', label: 'Content' },
    { id: 'headings', label: 'Headings', count: h1s.length + h2s.length },
    { id: 'links', label: 'Links', count: outlinks.length },
    { id: 'images', label: 'Images', count: images.length },
    { id: 'schema', label: 'Schema JSON-LD', count: schemas.length },
    { id: 'performance', label: 'Performance' },
    { id: 'evidence', label: 'Evidence & DOM' },
    { id: 'findings', label: 'Findings', count: pageFindings.length },
    { id: 'history', label: 'Snapshot Diffs' },
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-ink-950/40 backdrop-blur-xs flex justify-end">
      <div className="relative w-full max-w-4xl bg-paper dark:bg-paper-900 border-l border-line shadow-2xl flex flex-col h-full">
        <div className="p-5 border-b border-line bg-paper-subtle flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge tone={statusCode === 200 ? 'good' : statusCode && statusCode >= 400 ? 'bad' : 'warn'}>
                HTTP {statusCode ?? '—'}
              </Badge>
              <Badge tone={pageFindings.length > 0 ? 'bad' : 'good'}>
                {pageFindings.length} Finding{pageFindings.length !== 1 ? 's' : ''}
              </Badge>
              {schemas.length > 0 && <Badge tone="pine">{schemas.length} Schemas</Badge>}
            </div>
            <button onClick={onClose} className="p-1.5 rounded-lg text-ink-400 hover:text-ink hover:bg-paper-100">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex items-center gap-1.5 truncate">
            <span className="font-mono text-sm font-bold text-ink truncate select-all">{url}</span>
            <button onClick={handleCopyUrl} className="p-1 rounded text-ink-400 hover:text-ink shrink-0" title="Copy URL">
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            <a href={url} target="_blank" rel="noopener noreferrer" className="p-1 rounded text-ink-400 hover:text-ink shrink-0" title="Open live URL">
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar border-t border-line/60 pt-2 -mb-2">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`px-3 py-1.5 text-xs font-semibold whitespace-nowrap rounded-lg transition-colors flex items-center gap-1.5 ${
                  activeTab === t.id ? 'bg-primary text-primary-contrast' : 'text-ink-600 dark:text-ink-300 hover:bg-paper-100'
                }`}
              >
                {t.label}
                {t.count != null && t.count > 0 && (
                  <span className={`px-1.5 rounded-full text-[10px] font-mono ${activeTab === t.id ? 'bg-white/20 text-white' : 'bg-paper-200 text-ink-600'}`}>
                    {t.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="card p-3 bg-paper-subtle border border-line">
                  <span className="text-[11px] text-ink-400 font-semibold uppercase">Status</span>
                  <p className="text-base font-bold font-mono text-ink mt-0.5">HTTP {statusCode ?? '—'}</p>
                </div>
                <div className="card p-3 bg-paper-subtle border border-line">
                  <span className="text-[11px] text-ink-400 font-semibold uppercase">Canonical</span>
                  <p className="text-xs font-bold font-mono text-ink mt-0.5 truncate">
                    {!canonical ? 'Missing' : isCanonicalMatch ? 'Self-referencing' : 'Custom / Cross-URL'}
                  </p>
                </div>
                <div className="card p-3 bg-paper-subtle border border-line">
                  <span className="text-[11px] text-ink-400 font-semibold uppercase">Word Count</span>
                  <p className="text-base font-bold font-mono text-ink mt-0.5">{wordCount} words</p>
                </div>
                <div className="card p-3 bg-paper-subtle border border-line">
                  <span className="text-[11px] text-ink-400 font-semibold uppercase">H1 Count</span>
                  <p className="text-base font-bold font-mono text-ink mt-0.5">{h1s.length} tag(s)</p>
                </div>
              </div>

              <div className="card p-4 space-y-3 bg-paper-subtle border border-line">
                <h4 className="text-xs uppercase font-bold text-ink-500">Observed SERP Preview</h4>
                <div className="p-4 rounded-lg bg-white dark:bg-paper-950 border border-line space-y-1">
                  <span className="text-xs text-ink-400 block truncate">{url}</span>
                  <h5 className="text-base font-medium text-blue-700 dark:text-blue-400">{title || '(Missing <title> tag)'}</h5>
                  <p className="text-xs text-ink-600 dark:text-ink-300 line-clamp-2">{metaDesc || '(Missing meta description)'}</p>
                </div>
              </div>

              {pageFindings.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs uppercase font-bold text-ink-500">Defects Isolated To This URL ({pageFindings.length})</h4>
                  {pageFindings.map((f) => (
                    <div
                      key={f.finding_id}
                      onClick={() => onSelectFinding?.(f)}
                      className="p-3 rounded-lg border border-line bg-paper-subtle hover:border-ink-400 cursor-pointer flex items-center justify-between"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <Badge tone={f.severity === 'CRITICAL' ? 'bad' : 'warn'}>{f.severity}</Badge>
                          <span className="font-mono text-xs text-ink-400">{f.finding_id}</span>
                        </div>
                        <p className="text-xs font-semibold text-ink">{f.title}</p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-ink-400" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'technical' && (
            <div className="space-y-4">
              <h4 className="text-xs uppercase font-bold text-ink-500">Observed HTTP &amp; Network Directives</h4>
              <div className="grid gap-3 sm:grid-cols-2 text-xs">
                <div className="p-3 rounded-lg bg-paper-subtle border border-line space-y-1">
                  <span className="text-ink-400 uppercase font-mono text-[10px]">HTTP Status</span>
                  <p className="font-mono font-semibold text-ink">{statusCode ?? 'Not recorded'}</p>
                </div>
                <div className="p-3 rounded-lg bg-paper-subtle border border-line space-y-1">
                  <span className="text-ink-400 uppercase font-mono text-[10px]">Measured Crawl Depth</span>
                  <p className="font-mono font-semibold text-ink">{clickDepth != null ? `Depth ${clickDepth}` : 'Not measured'}</p>
                </div>
                <div className="p-3 rounded-lg bg-paper-subtle border border-line space-y-1">
                  <span className="text-ink-400 uppercase font-mono text-[10px]">Robots Directives</span>
                  <p className="font-mono font-semibold text-ink">{robotsMeta}</p>
                </div>
                <div className="p-3 rounded-lg bg-paper-subtle border border-line space-y-1">
                  <span className="text-ink-400 uppercase font-mono text-[10px]">Protocol</span>
                  <p className="font-mono font-semibold text-ink">{url.startsWith('https://') ? 'HTTPS' : url.startsWith('http://') ? 'HTTP (Unencrypted)' : 'Unknown'}</p>
                </div>
              </div>
              <div className="p-4 rounded-lg bg-paper-subtle border border-line space-y-2">
                <span className="text-xs font-bold text-ink">Canonical URL Tag</span>
                <p className="font-mono text-xs text-ink bg-paper p-2 rounded border border-line break-all">
                  {canonical || 'Missing <link rel="canonical"> tag'}
                </p>
              </div>
            </div>
          )}

          {activeTab === 'metadata' && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-paper-subtle border border-line space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-ink">Page Title Tag</span>
                  <span className="font-mono text-xs text-ink-500">{title.length} characters</span>
                </div>
                <p className="font-medium text-sm text-ink bg-paper p-2.5 rounded border border-line">{title || 'Missing'}</p>
              </div>
              <div className="p-4 rounded-lg bg-paper-subtle border border-line space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-ink">Meta Description</span>
                  <span className="font-mono text-xs text-ink-500">{metaDesc.length} characters</span>
                </div>
                <p className="text-xs text-ink-700 bg-paper p-2.5 rounded border border-line leading-relaxed">{metaDesc || 'Missing'}</p>
              </div>
            </div>
          )}

          {activeTab === 'content' && (
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-lg bg-paper-subtle border border-line">
                <span className="text-[10px] text-ink-400 font-semibold uppercase">Extracted Words</span>
                <p className="text-lg font-bold font-mono text-ink mt-0.5">{wordCount}</p>
              </div>
              <div className="p-3 rounded-lg bg-paper-subtle border border-line">
                <span className="text-[10px] text-ink-400 font-semibold uppercase">Content Depth</span>
                <p className="text-sm font-bold font-mono text-ink mt-1">
                  {wordCount > 600 ? 'Substantial' : wordCount >= 200 ? 'Moderate' : 'Thin (<200)'}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-paper-subtle border border-line">
                <span className="text-[10px] text-ink-400 font-semibold uppercase">Declared Language</span>
                <p className="text-sm font-bold font-mono text-ink mt-1">{language}</p>
              </div>
            </div>
          )}

          {activeTab === 'headings' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <span className="text-xs font-bold text-ink">Primary H1 ({h1s.length})</span>
                {h1s.length > 0 ? (
                  h1s.map((h, i) => <div key={i} className="p-2.5 rounded bg-paper-subtle border border-line text-xs font-semibold text-ink">{h}</div>)
                ) : (
                  <p className="text-xs text-rose-600 font-medium">Missing primary H1 tag.</p>
                )}
              </div>
              {h2s.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-xs font-bold text-ink">H2 Headings ({h2s.length})</span>
                  {h2s.map((h, i) => <div key={i} className="p-2 rounded bg-paper-subtle border border-line/60 text-xs text-ink-700">{h}</div>)}
                </div>
              )}
              {h3s.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-xs font-bold text-ink">H3 Headings ({h3s.length})</span>
                  {h3s.map((h, i) => <div key={i} className="p-2 rounded bg-paper-subtle border border-line/60 text-xs text-ink-600">{h}</div>)}
                </div>
              )}
            </div>
          )}

          {activeTab === 'links' && (
            <div className="space-y-4">
              <div className="p-3 rounded-lg bg-paper-subtle border border-line space-y-2">
                <span className="text-xs font-bold text-ink">Observed Inbound Links ({inlinks.length})</span>
                {inlinks.length > 0 ? (
                  <ul className="text-xs space-y-1 font-mono text-ink-600">
                    {inlinks.map((l: string, i: number) => <li key={i} className="truncate">• {l}</li>)}
                  </ul>
                ) : (
                  <p className="text-xs text-ink-500">No inbound link list attached to this page snapshot.</p>
                )}
              </div>
              <div className="p-3 rounded-lg bg-paper-subtle border border-line space-y-2">
                <span className="text-xs font-bold text-ink">Outbound Links ({outlinks.length} internal · {externalLinks.length} external)</span>
                {outlinks.slice(0, 20).map((l: string, i: number) => (
                  <div key={i} className="font-mono text-xs text-ink-600 truncate">→ {l}</div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'images' && (
            <div className="space-y-3">
              <span className="text-xs font-bold text-ink">Observed Page Images ({images.length})</span>
              {images.length > 0 ? (
                images.map((img: any, i: number) => (
                  <div key={i} className="p-2.5 rounded bg-paper-subtle border border-line text-xs flex items-center justify-between gap-2">
                    <span className="font-mono text-ink truncate">{img.src || img.url || 'image'}</span>
                    <Badge tone={img.alt ? 'good' : 'bad'}>{img.alt ? 'Has ALT' : 'Missing ALT'}</Badge>
                  </div>
                ))
              ) : (
                <p className="text-xs text-ink-500">No image asset records stored for this URL.</p>
              )}
            </div>
          )}

          {activeTab === 'schema' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-ink">Detected Schema.org Types</span>
                <Badge tone={schemas.length > 0 ? 'good' : 'warn'}>{schemas.length} Types</Badge>
              </div>
              {schemas.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {schemas.map((s) => (
                    <span key={s} className="px-2.5 py-1 rounded-md text-xs font-mono font-semibold bg-purple-50 text-purple-700 border border-purple-200">{s}</span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-ink-500">No structured data blocks detected in this URL snapshot.</p>
              )}
            </div>
          )}

          {activeTab === 'performance' && (
            <div className="space-y-4">
              <h4 className="text-xs uppercase font-bold text-ink-500">Observed Core Web Vitals &amp; Latency (Zero Fabricated Estimates)</h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-paper-subtle border border-line">
                  <span className="text-[10px] text-ink-400 font-semibold uppercase">LCP (Lab/Field)</span>
                  <p className="text-base font-bold font-mono text-ink mt-0.5">{lcpMs != null ? `${(lcpMs / 1000).toFixed(2)}s` : 'Not measured'}</p>
                </div>
                <div className="p-3 rounded-lg bg-paper-subtle border border-line">
                  <span className="text-[10px] text-ink-400 font-semibold uppercase">CLS</span>
                  <p className="text-base font-bold font-mono text-ink mt-0.5">{clsVal != null ? clsVal.toFixed(3) : 'Not measured'}</p>
                </div>
                <div className="p-3 rounded-lg bg-paper-subtle border border-line">
                  <span className="text-[10px] text-ink-400 font-semibold uppercase">INP</span>
                  <p className="text-base font-bold font-mono text-ink mt-0.5">{inpMs != null ? `${Math.round(inpMs)}ms` : 'Not measured'}</p>
                </div>
                <div className="p-3 rounded-lg bg-paper-subtle border border-line">
                  <span className="text-[10px] text-ink-400 font-semibold uppercase">TTFB</span>
                  <p className="text-base font-bold font-mono text-ink mt-0.5">{ttfbMs != null ? `${Math.round(ttfbMs)}ms` : 'Not measured'}</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-ink">Raw HTML, Rendered DOM &amp; Screenshot Capture</span>
                <div className="flex items-center gap-1 border border-line rounded-lg p-0.5 bg-paper-subtle">
                  {(['rendered', 'raw', 'screenshot'] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setDomViewMode(m)}
                      className={`px-2.5 py-1 text-xs rounded capitalize ${domViewMode === m ? 'bg-paper font-semibold text-ink shadow-xs' : 'text-ink-500'}`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>
              {domViewMode === 'screenshot' ? (
                screenshotUrl ? (
                  <img src={screenshotUrl} alt={`Captured screenshot of ${url}`} className="rounded-lg border border-line max-h-96 object-contain" />
                ) : (
                  <div className="p-4 rounded-lg bg-paper-subtle border border-line text-xs text-ink-500">
                    No screenshot artifact was captured for this URL during this crawl run.
                  </div>
                )
              ) : (
                <pre className="p-3 rounded-lg bg-paper-950 text-paper-50 font-mono text-[11px] max-h-80 overflow-auto whitespace-pre-wrap">
                  {(domViewMode === 'raw' ? rawHtml : renderedHtml) || `No ${domViewMode} HTML snapshot stored for this URL.`}
                </pre>
              )}
            </div>
          )}

          {activeTab === 'findings' && (
            <div className="space-y-3">
              <span className="text-xs font-bold text-ink">All Findings for this URL ({pageFindings.length})</span>
              {pageFindings.length > 0 ? (
                pageFindings.map((f) => (
                  <div key={f.finding_id} className="p-4 rounded-xl border border-line bg-paper-subtle space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge tone={f.severity === 'CRITICAL' ? 'bad' : 'warn'}>{f.severity}</Badge>
                        <span className="font-mono text-xs text-ink-400">{f.finding_id}</span>
                      </div>
                      <Button size="sm" variant="secondary" onClick={() => onSelectFinding?.(f)} className="text-xs">
                        Inspect Patch
                      </Button>
                    </div>
                    <h5 className="text-sm font-semibold text-ink">{f.title}</h5>
                    <p className="text-xs text-ink-600">{f.recommendation || f.description}</p>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-xs text-ink-500 bg-paper-subtle rounded-xl border border-line">
                  No defects flagged on this specific URL.
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-bold text-ink">Snapshot Comparison</span>
                {allPages.length > 1 && (
                  <select
                    value={compareUrl}
                    onChange={(e) => setCompareUrl(e.target.value)}
                    className="py-1 px-2 text-xs rounded border border-line bg-paper text-ink max-w-xs"
                  >
                    <option value="">Select snapshot to compare...</option>
                    {allPages
                      .filter((p) => String(p.url) !== url)
                      .map((p) => (
                        <option key={String(p.url)} value={String(p.url)}>
                          {String(p.url)}
                        </option>
                      ))}
                  </select>
                )}
              </div>
              {comparedPage ? (
                <table className="w-full text-left text-xs border border-line rounded-lg overflow-hidden">
                  <thead>
                    <tr className="bg-paper-subtle border-b border-line text-[10px] uppercase text-ink-400">
                      <th className="p-2.5">Signal</th>
                      <th className="p-2.5">Current URL</th>
                      <th className="p-2.5">Compared Snapshot</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line font-mono text-[11px]">
                    <tr><td className="p-2.5 font-sans font-semibold">HTTP Status</td><td className="p-2.5">{statusCode ?? '—'}</td><td className="p-2.5">{comparedPage.status_code ?? '—'}</td></tr>
                    <tr><td className="p-2.5 font-sans font-semibold">Title</td><td className="p-2.5">{title || '—'}</td><td className="p-2.5">{comparedPage.title || '—'}</td></tr>
                    <tr><td className="p-2.5 font-sans font-semibold">Canonical</td><td className="p-2.5">{canonical || '—'}</td><td className="p-2.5">{comparedPage.canonical_url || '—'}</td></tr>
                    <tr><td className="p-2.5 font-sans font-semibold">Word Count</td><td className="p-2.5">{wordCount}</td><td className="p-2.5">{comparedPage.word_count ?? 0}</td></tr>
                    <tr><td className="p-2.5 font-sans font-semibold">TTFB (ms)</td><td className="p-2.5">{ttfbMs ?? '—'}</td><td className="p-2.5">{comparedPage.ttfb_ms ?? '—'}</td></tr>
                  </tbody>
                </table>
              ) : (
                <div className="p-4 rounded-lg bg-paper-subtle border border-line text-xs text-ink-500">
                  Recorded in Audit ID <code>{report.analysis_id || report.report_id}</code>. Select another crawled snapshot above or run a follow-up audit to compare side-by-side diffs.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
