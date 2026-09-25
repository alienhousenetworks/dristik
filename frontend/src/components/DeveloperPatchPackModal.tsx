import React, { useState, useEffect } from 'react';

interface DeveloperPatchPackModalProps {
  analysisId: string;
  domain: string;
  isOpen: boolean;
  onClose: () => void;
}

export function DeveloperPatchPackModal({
  analysisId,
  domain,
  isOpen,
  onClose,
}: DeveloperPatchPackModalProps) {
  const [activeFile, setActiveFile] = useState<string>('README_DEV_INSTALL.md');
  const [files, setFiles] = useState<Record<string, string>>({});
  const [notionBlock, setNotionBlock] = useState<string>('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen && Object.keys(files).length === 0) {
      setIsLoading(true);
      fetch(`/api/v1/analyses/${analysisId}/patch-pack/files`, {
        credentials: 'include',
      })
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          if (data.files) {
            setFiles(data.files);
            if (!data.files['README_DEV_INSTALL.md'] && data.file_names?.length) {
              setActiveFile(data.file_names[0]);
            }
          }
        })
        .catch((err) => console.error('Error fetching patch files:', err))
        .finally(() => setIsLoading(false));

      fetch(`/api/v1/analyses/${analysisId}/patch-pack/notion`, {
        credentials: 'include',
      })
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          if (data.notion_markdown) {
            setNotionBlock(data.notion_markdown);
          }
        })
        .catch((err) => console.error('Error fetching notion markdown:', err));
    }
  }, [isOpen, analysisId]);

  if (!isOpen) return null;

  const handleDownloadZip = async () => {
    setIsDownloading(true);
    try {
      const res = await fetch(`/api/v1/analyses/${analysisId}/patch-pack/zip`, {
        credentials: 'include',
      });
      if (!res.ok) {
        let errMsg = `Failed to download ZIP (HTTP ${res.status})`;
        try {
          const errData = await res.json();
          if (errData.detail) errMsg = errData.detail;
        } catch (_) {}
        alert(errMsg);
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${domain.replace(/\./g, '_')}_dristik_patch_pack.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading patch pack:', err);
      alert('Network error downloading patch pack.');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleCopy = async (key: string, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const fileKeys = Object.keys(files);

  return (
    <div className="scrim fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4">
      <div className="sheet rounded-lg shadow-xl max-w-4xl w-full border border-line overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-line flex items-center justify-between bg-paper-50 text-ink">
          <div className="flex items-center gap-2.5">
            <span className="w-3 h-3 rounded-full bg-good"></span>
            <div>
              <h2 className="label text-xs font-bold text-ink">
                Developer Patch Pack — Ready to Ship
              </h2>
              <p className="text-xs text-ink-500">
                15-Minute Drop-In Remediation Package for {domain}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleDownloadZip}
              disabled={isDownloading}
              className="btn-primary disabled:opacity-50 font-semibold text-xs px-3.5 py-1.5 rounded shadow transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              {isDownloading ? 'Preparing ZIP...' : 'Download ZIP Archive'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="text-ink-400 hover:text-ink text-lg font-bold px-2 py-1"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Action Banner */}
        <div className="bg-paper-100 border-b border-line px-6 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <p className="text-ink-700">
            One ZIP or Notion block: <span className="font-semibold text-ink">schema.jsonld</span>, <span className="font-semibold text-ink">metadata.html</span>, <span className="font-semibold text-ink">faq.html</span>, <span className="font-semibold text-ink">llms.txt</span>, and <span className="font-semibold text-ink">robots.txt</span>. Not generic advice.
          </p>
          <button
            type="button"
            onClick={() => handleCopy('notion', notionBlock || 'Loading Notion Markdown...')}
            className="sheet border border-line hover:border-ink-400 text-ink font-semibold px-3 py-1 rounded shadow-2xs flex items-center gap-1.5 transition-colors"
          >
            {copiedKey === 'notion' ? (
              <span className="text-good font-bold">✓ Copied Notion Block!</span>
            ) : (
              <span>📋 Copy 1-Click Notion Block</span>
            )}
          </button>
        </div>

        {/* Content Body: Tabs & Code Viewer */}
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
          {/* File Tab List */}
          <div className="w-full md:w-56 bg-paper-50 border-r border-line p-2 space-y-1 shrink-0 overflow-y-auto">
            {fileKeys.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setActiveFile(key)}
                className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-colors flex items-center justify-between ${
                  activeFile === key
                    ? 'sheet font-bold text-ink shadow-2xs border border-line'
                    : 'text-ink-700 hover:bg-paper-200'
                }`}
              >
                <span className="truncate">{key}</span>
                {key.endsWith('.jsonld') && <span className="text-[9px] px-1 bg-amber-100 text-warn rounded">LD</span>}
                {key.endsWith('.txt') && <span className="text-[9px] px-1 bg-paper-200 text-ink rounded">TXT</span>}
                {key.endsWith('.html') && <span className="text-[9px] px-1 bg-pine-100 text-pine rounded">HTML</span>}
              </button>
            ))}
          </div>

          {/* Active File Content Viewer */}
          <div className="flex-1 flex flex-col overflow-hidden bg-paper-200/50 text-ink">
            <div className="px-4 py-2 bg-paper-100 border-b border-line flex items-center justify-between text-xs">
              <span className="font-mono text-ink-500">{activeFile}</span>
              <button
                type="button"
                onClick={() => handleCopy(activeFile, files[activeFile] || '')}
                className="text-pine hover:underline font-medium flex items-center gap-1 transition-colors"
              >
                {copiedKey === activeFile ? (
                  <span className="text-good font-bold">✓ Copied!</span>
                ) : (
                  <span>Copy File Content</span>
                )}
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {isLoading ? (
                <div className="p-8 text-center text-ink-500 font-mono text-xs">
                  Generating patch files...
                </div>
              ) : (
                <pre className="font-mono text-xs text-ink leading-relaxed whitespace-pre-wrap">
                  {files[activeFile] || '// Select a file from the sidebar'}
                </pre>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-line bg-paper-50 flex items-center justify-between text-xs text-ink-500">
          <span>Target deploy time: 15 minutes · Compatible with Webflow, WordPress, Next.js, Shopify</span>
          <button
            type="button"
            onClick={onClose}
            className="text-ink hover:underline font-medium px-3 py-1"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
