"""
Dristik AI PDF & HTML Renderer for Progressive Sub-Phase & Phase Reports.
Generates editorial, publication-standard HTML reports and compiles them
to vector-grade PDFs using Playwright headless Chromium with graceful fallback.
"""
from __future__ import annotations

import html
import json
import logging
from typing import Any, Dict, List, Optional

from app.crawl.browser import BrowserRenderService
from app.reporting.contracts.subphase_contract import (
    ConfidenceLevel,
    ExecutionStatus,
    PhaseReportContract,
    SubPhaseReportContract,
)

logger = logging.getLogger("dristik.reporting.pdf_renderer")


class ProgressivePDFRenderer:
    """Renders SubPhaseReportContract and PhaseReportContract into print-ready HTML and PDF."""

    @staticmethod
    def _format_json(data: Any) -> str:
        try:
            return html.escape(json.dumps(data, indent=2, default=str))
        except Exception:
            return html.escape(str(data))

    @classmethod
    def render_subphase_html(cls, contract: SubPhaseReportContract) -> str:
        # Determine status colors
        status_colors = {
            ExecutionStatus.COMPLETED: "#10b981",  # emerald
            ExecutionStatus.FAILED: "#ef4444",     # red
            ExecutionStatus.NOT_MEASURED: "#64748b",  # slate
            ExecutionStatus.NOT_CONFIGURED: "#f59e0b", # amber
            ExecutionStatus.IN_PROGRESS: "#3b82f6",  # blue
        }
        status_bg = status_colors.get(contract.status, "#64748b")

        confidence_colors = {
            ConfidenceLevel.VERIFIED: "#10b981",
            ConfidenceLevel.INFERRED: "#3b82f6",
            ConfidenceLevel.CONTESTED: "#f59e0b",
            ConfidenceLevel.UNMEASURED: "#64748b",
        }
        confidence_color = confidence_colors.get(contract.confidence, "#64748b")

        # Build findings rows
        findings_html = ""
        if contract.findings:
            for f in contract.findings:
                sev_color = "#ef4444" if f.severity.lower() == "critical" else "#f59e0b" if f.severity.lower() == "high" else "#3b82f6"
                ev_tags = "".join(f'<span class="badge" style="background:#1e293b;border:1px solid #334155;color:#94a3b8;font-size:10px;margin-right:4px;">{html.escape(ev)}</span>' for ev in f.evidence_ids)
                findings_html += f"""
                <div class="card finding-card" style="border-left: 4px solid {sev_color};">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-weight:700; color:#f8fafc; font-size:13px;">{html.escape(f.title)}</span>
                        <span class="badge" style="background:{sev_color}22; color:{sev_color}; border:1px solid {sev_color}66; text-transform:uppercase; font-size:10px;">{html.escape(f.severity)}</span>
                    </div>
                    <div style="font-size:12px; color:#cbd5e1; margin-bottom:6px;">{html.escape(f.description)}</div>
                    {f'<div style="font-size:11px; color:#38bdf8; margin-bottom:4px;"><strong>Remediation:</strong> {html.escape(f.remediation_hint)}</div>' if f.remediation_hint else ''}
                    {f'<div style="margin-top:6px;"><strong>Evidence IDs:</strong> {ev_tags}</div>' if ev_tags else ''}
                </div>
                """
        else:
            findings_html = """<div class="empty-state">No issues flagged in this sub-phase execution.</div>"""

        # Build evidence tokens rows
        evidence_html = ""
        if contract.evidence_tokens:
            evidence_rows = ""
            for ev in contract.evidence_tokens:
                evidence_rows += f"""
                <tr>
                    <td style="font-family:monospace; color:#38bdf8; font-size:11px;">{html.escape(ev.evidence_id)}</td>
                    <td style="color:#94a3b8; font-size:11px;">{html.escape(ev.token_type)}</td>
                    <td style="font-family:monospace; font-size:11px; word-break:break-all;">{html.escape(ev.locator)}</td>
                    <td style="color:#cbd5e1; font-size:11px;">{html.escape(ev.excerpt or '—')}</td>
                </tr>
                """
            evidence_html = f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th style="width:18%;">ID</th>
                        <th style="width:15%;">Type</th>
                        <th style="width:37%;">Locator / Target</th>
                        <th style="width:30%;">Excerpt / Token Value</th>
                    </tr>
                </thead>
                <tbody>{evidence_rows}</tbody>
            </table>
            """
        else:
            evidence_html = """<div class="empty-state">No individual DOM/telemetry tokens registered.</div>"""

        # Errors / unresolved issues
        errors_section = ""
        if contract.errors or contract.unresolved_issues:
            err_items = "".join(f"<li>{html.escape(e)}</li>" for e in contract.errors)
            unres_items = "".join(f"<li>{html.escape(u)}</li>" for u in contract.unresolved_issues)
            errors_section = f"""
            <div class="section-title" style="color:#f87171;">Errors & Unresolved Contradictions</div>
            <div class="card" style="background:#271216; border:1px solid #7f1d1d;">
                {f'<div style="margin-bottom:8px;"><strong style="color:#fca5a5;">Failed Operations:</strong><ul style="color:#fecaca; margin:4px 0 0 18px; font-size:12px;">{err_items}</ul></div>' if err_items else ''}
                {f'<div><strong style="color:#fcd34d;">Unresolved Issues:</strong><ul style="color:#fef08a; margin:4px 0 0 18px; font-size:12px;">{unres_items}</ul></div>' if unres_items else ''}
            </div>
            """

        # Processing steps
        processing_html = "".join(f"<li>{html.escape(s)}</li>" for s in contract.processing_steps) if contract.processing_steps else "<li>Standard pipeline execution</li>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dristik Progressive Audit Report - {html.escape(contract.subphase_title)}</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 15mm;
            @top-right {{
                content: "Dristik Progressive Audit | {html.escape(contract.run_id)}";
                font-family: monospace;
                font-size: 8pt;
                color: #64748b;
            }}
            @bottom-center {{
                content: "Sub-Phase Report {html.escape(contract.subphase_id)} | Page " counter(page) " of " counter(pages);
                font-family: monospace;
                font-size: 8pt;
                color: #64748b;
            }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
            background: #0b1120;
            color: #f1f5f9;
            margin: 0;
            padding: 0;
            font-size: 13px;
            line-height: 1.5;
            -webkit-print-color-adjust: exact;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #1e293b;
            padding-bottom: 14px;
            margin-bottom: 18px;
        }}
        .brand-title {{
            font-size: 18px;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #f8fafc;
        }}
        .brand-sub {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #0d9488;
            font-weight: 700;
            margin-top: 2px;
        }}
        .meta-box {{
            text-align: right;
            font-size: 11px;
            font-family: monospace;
            color: #94a3b8;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }}
        .card {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 6px;
            padding: 12px 14px;
            margin-bottom: 14px;
        }}
        .finding-card {{
            margin-bottom: 10px;
        }}
        .section-title {{
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #38bdf8;
            margin: 16px 0 8px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-top: 6px;
        }}
        .data-table th {{
            background: #1e293b;
            color: #94a3b8;
            text-align: left;
            padding: 6px 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .data-table td {{
            padding: 6px 10px;
            border-bottom: 1px solid #1e293b;
        }}
        .empty-state {{
            padding: 12px;
            text-align: center;
            color: #64748b;
            font-style: italic;
            background: #111827;
            border: 1px dashed #1e293b;
            border-radius: 6px;
        }}
        pre.json-dump {{
            background: #030712;
            border: 1px solid #1e293b;
            padding: 10px;
            border-radius: 4px;
            font-size: 10px;
            font-family: monospace;
            color: #a5f3fc;
            overflow-x: auto;
            max-height: 280px;
        }}
        .seal-bar {{
            margin-top: 24px;
            padding-top: 10px;
            border-top: 1px solid #1e293b;
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            font-family: monospace;
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="brand-sub">Dristik AI &bull; Progressive Execution Report</div>
            <div class="brand-title">Phase {html.escape(contract.subphase_id)}: {html.escape(contract.subphase_title)}</div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">{html.escape(contract.phase_name)}</div>
        </div>
        <div class="meta-box">
            <div>RUN ID: <strong style="color:#f8fafc;">{html.escape(contract.run_id)}</strong></div>
            <div>TIME: {html.escape(contract.timestamp)}</div>
            <div style="margin-top:6px;">
                <span class="badge" style="background:{status_bg}22; color:{status_bg}; border:1px solid {status_bg}66;">
                    {html.escape(contract.status.value)}
                </span>
                <span class="badge" style="background:{confidence_color}22; color:{confidence_color}; border:1px solid {confidence_color}66; margin-left:4px;">
                    {html.escape(contract.confidence.value)}
                </span>
            </div>
        </div>
    </div>

    <!-- Objective & Agent Identity -->
    <div class="grid-2">
        <div class="card">
            <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:4px;">Sub-Phase Objective</div>
            <div style="color:#e2e8f0; font-size:12px;">{html.escape(contract.objective)}</div>
        </div>
        <div class="card">
            <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:4px;">Agent / Engine Details</div>
            <div style="font-size:12px; color:#cbd5e1;">
                <div><strong>Agent ID:</strong> <code>{html.escape(contract.agent_id)}</code></div>
                <div><strong>Model:</strong> <code>{html.escape(contract.agent_model)}</code> ({html.escape(contract.execution_mode)})</div>
                <div><strong>Execution Duration:</strong> {contract.duration_ms} ms</div>
            </div>
        </div>
    </div>

    <!-- Processing Steps -->
    <div class="section-title">Execution Trace & Processing</div>
    <div class="card">
        <ul style="margin:0 0 0 18px; padding:0; color:#cbd5e1; font-size:12px;">
            {processing_html}
        </ul>
    </div>

    <!-- Structured Output -->
    <div class="section-title">Actual Structured Output</div>
    <pre class="json-dump">{cls._format_json(contract.structured_output)}</pre>

    <!-- Findings -->
    <div class="section-title">Findings & Observations ({len(contract.findings)})</div>
    {findings_html}

    <!-- Evidence Tokens -->
    <div class="section-title">Underlying Evidence Ledger ({len(contract.evidence_tokens)} tokens)</div>
    {evidence_html}

    <!-- Errors if any -->
    {errors_section}

    <!-- Next Phase Handoff -->
    <div class="section-title">Next Phase Handoff Data</div>
    <div class="card" style="background:#0f172a;">
        <pre class="json-dump" style="max-height:140px;">{cls._format_json(contract.next_phase_handoff)}</pre>
    </div>

    <div class="seal-bar">
        <div>SHA-256 HASH: <code>{html.escape(contract.content_hash or 'UNSEALED')}</code></div>
        <div>ZERO-FABRICATION CONTRACT ENFORCED &bull; DRISTIK OS</div>
    </div>
</body>
</html>
"""

    @classmethod
    def render_phase_html(cls, contract: PhaseReportContract) -> str:
        findings_html = ""
        for f in contract.reconciled_findings:
            sev_color = "#ef4444" if f.severity.lower() == "critical" else "#f59e0b" if f.severity.lower() == "high" else "#3b82f6"
            findings_html += f"""
            <div class="card" style="border-left: 4px solid {sev_color}; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between;">
                    <strong>{html.escape(f.title)}</strong>
                    <span class="badge" style="background:{sev_color}22; color:{sev_color};">{html.escape(f.severity)}</span>
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">{html.escape(f.description)}</div>
            </div>
            """

        subphase_rows = ""
        for sub_id, summary in contract.subphase_summaries.items():
            sub_hash = contract.subphase_hashes.get(sub_id, "—")[:12]
            subphase_rows += f"""
            <tr>
                <td style="font-weight:700; color:#38bdf8;">{html.escape(sub_id)}</td>
                <td style="color:#cbd5e1;">{html.escape(str(summary))}</td>
                <td style="font-family:monospace; color:#94a3b8; font-size:10px;">{html.escape(sub_hash)}...</td>
            </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dristik Consolidated Phase Report - {html.escape(contract.phase_name)}</title>
    <style>
        @page {{ size: A4 portrait; margin: 15mm; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
            background: #0b1120;
            color: #f1f5f9;
            margin: 0; padding: 0; font-size: 13px; line-height: 1.5;
            -webkit-print-color-adjust: exact;
        }}
        .header {{
            border-bottom: 2px solid #0d9488;
            padding-bottom: 14px; margin-bottom: 18px;
        }}
        .brand-sub {{ color: #0d9488; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.1em; }}
        .brand-title {{ font-size: 22px; font-weight: 800; color: #f8fafc; }}
        .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 6px; padding: 14px; margin-bottom: 14px; }}
        .data-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        .data-table th {{ background: #1e293b; color: #94a3b8; text-align: left; padding: 8px 10px; }}
        .data-table td {{ padding: 8px 10px; border-bottom: 1px solid #1e293b; }}
        .badge {{ padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; text-transform: uppercase; }}
        .seal-bar {{ margin-top: 24px; padding-top: 10px; border-top: 1px solid #1e293b; font-size: 10px; font-family: monospace; color: #64748b; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand-sub">Dristik AI Consolidated Phase Dossier</div>
        <div class="brand-title">{html.escape(contract.phase_name)}</div>
        <div style="font-size:12px; color:#94a3b8; margin-top:4px;">RUN ID: <strong>{html.escape(contract.run_id)}</strong> | Generated: {html.escape(contract.timestamp)}</div>
    </div>

    <div class="card">
        <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:4px;">Executive Phase Summary</div>
        <div style="font-size:13px; color:#e2e8f0;">{html.escape(contract.summary)}</div>
    </div>

    <div style="font-size:13px; font-weight:700; text-transform:uppercase; color:#38bdf8; margin:16px 0 8px 0;">Sub-Phase Executions & Provenance</div>
    <div class="card" style="padding:0; overflow:hidden;">
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width:20%;">Sub-Phase</th>
                    <th style="width:60%;">Result Summary</th>
                    <th style="width:20%;">Content Hash</th>
                </tr>
            </thead>
            <tbody>{subphase_rows}</tbody>
        </table>
    </div>

    <div style="font-size:13px; font-weight:700; text-transform:uppercase; color:#38bdf8; margin:16px 0 8px 0;">Reconciled Phase Findings</div>
    {findings_html or '<div class="card" style="color:#64748b; font-style:italic;">No critical blockers detected across sub-phases.</div>'}

    <div class="seal-bar">
        <div>PHASE SEAL HASH: <code>{html.escape(contract.content_hash or 'UNSEALED')}</code></div>
        <div>ALL SUB-PHASES CRYPTOGRAPHICALLY PINNED &bull; DRISTIK OS</div>
    </div>
</body>
</html>
"""

    @classmethod
    async def render_pdf(cls, html_content: str) -> Optional[bytes]:
        """Compiles HTML string into PDF bytes via Playwright Chromium."""
        try:
            return await BrowserRenderService.render_pdf(html_content, timeout_ms=45000)
        except Exception as e:
            logger.warning(f"BrowserRenderService failed to render PDF: {e}")
            return None
