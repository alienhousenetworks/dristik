import React, { useState } from 'react';

interface WhatsAppShareButtonProps {
  analysisId: string;
  domain: string;
  summaryText?: string;
}

export function WhatsAppShareButton({ analysisId, domain, summaryText }: WhatsAppShareButtonProps) {
  const [copied, setCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [text, setText] = useState<string>(summaryText || '');

  const handleOpenShare = () => {
    if (!text) {
      fetch(`/api/v1/analyses/${analysisId}/whatsapp-summary`, {
        credentials: 'include',
      })
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          if (data.summary_text) {
            setText(data.summary_text);
            window.open(data.whatsapp_url, '_blank');
          }
        })
        .catch(() => {
          const fallback = `*DRISTIK AI AUDIT — ${domain.toUpperCase()}*\nView executive deliverable: https://app.dristik.ai`;
          window.open(`https://wa.me/?text=${encodeURIComponent(fallback)}`, '_blank');
        });
    } else {
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
    }
  };

  const handleCopyText = async () => {
    const textToCopy = text || `*DRISTIK AI AUDIT — ${domain.toUpperCase()}*\nView executive deliverable: https://app.dristik.ai`;
    await navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative inline-block">
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={handleOpenShare}
          className="bg-good/10 hover:bg-good/10 text-white font-semibold text-xs px-3.5 py-2 rounded-md shadow-xs transition-colors flex items-center gap-1.5"
        >
          <span className="text-sm">💬</span>
          WhatsApp 1-Pager
        </button>

        <button
          type="button"
          onClick={() => setShowPreview(!showPreview)}
          title="Preview or Copy WhatsApp Text"
          className="border border-line hover:border-line bg-paper-50 text-ink-700 text-xs px-2 py-2 rounded-md transition-colors shadow-2xs"
        >
          ▼
        </button>
      </div>

      {showPreview && (
        <div className="absolute right-0 top-full mt-2 w-80 md:w-96 bg-paper-50 border border-line rounded-lg shadow-xl p-4 z-50 text-xs space-y-3">
          <div className="flex items-center justify-between border-b border-line pb-2">
            <span className="font-bold text-ink-700">C-Suite WhatsApp 1-Pager Preview</span>
            <button
              type="button"
              onClick={() => setShowPreview(false)}
              className="text-ink-400 hover:text-ink-600 font-bold"
            >
              ✕
            </button>
          </div>

          <pre className="p-3 bg-good/10 border border-good/30 rounded text-[11px] font-mono text-ink-700 whitespace-pre-wrap max-h-60 overflow-y-auto">
            {text || `*DRISTIK AI EXECUTIVE AUDIT — ${domain.toUpperCase()}*\nLoading verified summary...`}
          </pre>

          <div className="flex items-center justify-between gap-2 pt-1">
            <button
              type="button"
              onClick={handleCopyText}
              className="text-xs text-ink-700 font-medium hover:text-ink border border-line px-3 py-1 rounded"
            >
              {copied ? '✓ Copied Text' : 'Copy Text'}
            </button>
            <button
              type="button"
              onClick={handleOpenShare}
              className="bg-good/10 hover:bg-good/10 text-white font-semibold text-xs px-3 py-1 rounded shadow-xs"
            >
              Open WhatsApp Web
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
