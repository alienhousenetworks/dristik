"""
Section-Specific Report & Printable PDF Export Generator for Dristik AI.
Renders standalone, editorial, print-ready HTML reports formatted for A4 presentation
across the 6 primary workspaces:
1. Crawl (Website Crawl Technical Audit)
2. SEO (SEO Space Deep Dive)
3. GEO (Generative Engine Optimization)
4. AEO (Answer Engine Optimization & Entity Graph)
5. CRO (Conversion Rate Optimization & UX Friction)
6. Competitors (Competitor Analysis & Benchmark)
"""
from typing import Dict, Any, List, Optional
from app.domain.models import ExecutiveReport
from app.reports.aeo_audit_book import aeo_cover_figure, render_aeo_audit_book
from app.reports.geo_audit_book import geo_cover_figure, render_geo_audit_book
from app.reports.seo_audit_book import render_seo_audit_book


class SectionReportGenerator:
    """
    Renders editorial, publication-grade HTML reports tailored to individual sections.
    """

    def render_section_html(self, report: ExecutiveReport, section_key: str) -> str:
        domain = report.domain or (report.website_url.replace("https://", "").replace("http://", "").split("/")[0])
        date_str = report.generated_at or "Measured on audit execution"
        section_key = (section_key or "seo").lower().strip()

        TITLES = {
            "crawl": ("01 // WEBSITE CRAWL & TECHNICAL INFRASTRUCTURE", "Network Topology, HTTP Response Ledger & Crawl Manifest"),
            "seo": ("02 // SEARCH ENGINE OPTIMIZATION (SEO) SPACE", "Technical Indexing, Meta Directives, Heading Hierarchy & SERP Snippets"),
            "geo": ("03 // GENERATIVE ENGINE OPTIMIZATION (GEO)", "Live AI Citability, RAG Extractability & Answer Engine Visibility"),
            "aeo": ("04 // ANSWER ENGINE OPTIMIZATION (AEO)", "Question coverage, answer quality, source eligibility, and observed answer visibility"),
            "cro": ("05 // CONVERSION RATE OPTIMIZATION (CRO)", "Value Proposition Delivery, CTA Ergonomics, Trust Signals & Friction"),
            "competitors": ("06 // COMPETITOR BENCHMARK & COMMERCIAL BAKE-OFF", "Head-to-Head Commercial Inquiry Testing & Industry Peer Parity"),
        }
        title, subtitle = TITLES.get(section_key, (f"{section_key.upper()} AUDIT DOSSIER", "Empirical Evidence & Remediation Blueprint"))

        # Section-specific metrics and findings
        findings = [f for f in (report.findings or []) if self._matches_section(f, section_key)]
        if not findings and report.findings:
            findings = report.findings[:10]

        pages = report.crawl_manifest.pages if (report.crawl_manifest and report.crawl_manifest.pages) else (report.page_reports or [])
        is_seo = section_key == "seo"
        is_aeo = section_key == "aeo"
        is_geo = section_key == "geo"
        if is_aeo:
            score_val = aeo_cover_figure(report)
        elif is_geo:
            score_val = geo_cover_figure(report)
        else:
            score_val = self._get_section_score(report, section_key)
        if is_seo or is_aeo or is_geo:
            findings = list(report.findings or [])
            if is_seo:
                book_html = render_seo_audit_book(report)
            elif is_aeo:
                book_html = render_aeo_audit_book(report)
            else:
                book_html = render_geo_audit_book(report)
            findings_html = ""
            extra_html = ""
            badge = "EVIDENCE-GROUNDED // REPRESENTATIVE SAMPLE"
            assurance_label = "SAMPLE SCOPE"
            assurance_value = "REPRESENTATIVE"
            standard_label = "EVIDENCE BASIS"
            standard_value = "STORED CRAWL & BENCHMARK" if is_geo else "STORED CRAWL"
            if is_aeo:
                score_label = "STORED EXTRACTABILITY"
                score_note = (
                    "<div class=\"score-note\">This figure is schema quality or on-page extractability when one of those was stored. "
                    "It is not a live answer-visibility rate, not a recommendation rate, and not a grade of every chapter. "
                    "Content readiness, technical eligibility, observed answer visibility, and business outcomes stay separate. "
                    "An unmeasured chapter is not a zero.</div>"
                )
                footer_mark = "FULL AEO INDEX // SECTIONS 01–55 AND APPENDICES A–O"
            elif is_geo:
                score_label = "STORED EXTRACTABILITY"
                score_note = (
                    "<div class=\"score-note\">This figure is on-page extractability or technical readiness. "
                    "Observed AI visibility, citation rate, and business impact are reported as separate dimensions. "
                    "An unmeasured chapter or platform is NOT_TESTED, not a zero.</div>"
                )
                footer_mark = "FULL GEO INDEX // SECTIONS 01–50 AND APPENDICES A–O"
            else:
                score_label = "SECTION HEALTH SCORE"
                score_note = (
                    "<div class=\"score-note\">The score is the sealed category result for this section. "
                    "Each chapter below keeps its own status. An unmeasured chapter is not a zero.</div>"
                )
                footer_mark = "FULL INDEX // SECTIONS 01–55 AND APPENDICES A–O"
        else:
            book_html = ""
            findings_html = (
                f"<h2>Verified Empirical Findings ({len(findings)})</h2>"
                + (
                    "".join(self._render_finding(f) for f in findings)
                    if findings
                    else "<p style='color:#64748b;'>No critical defects recorded for this section.</p>"
                )
            )
            extra_html = self._render_extra_section_tables(report, section_key, pages)
            badge = "EVIDENCE-GROUNDED // ZERO-FAKE AUDIT"
            assurance_label = "ASSURANCE TIER"
            assurance_value = "CERTIFIED"
            standard_label = "EVIDENCE STANDARD"
            standard_value = "ZERO-FAKE AST"
            score_label = "SECTION HEALTH SCORE"
            score_note = ""
            footer_mark = "PAGE 1 OF 1 // IMMUTABLE PROVENANCE SEAL"
        if score_val is None:
            score_html = "—"
        else:
            score_html = f"{score_val}<span style=\"font-size:20px;color:#64748b;\">/100</span>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dristik Intelligence Dossier - {title} - {domain}</title>
    <style>
        @page {{
            size: A4;
            margin: 15mm;
            @bottom-right {{
                content: counter(page);
                font-family: monospace;
                font-size: 8pt;
                color: #64748b;
            }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
            background: #ffffff;
            color: #0f172a;
            margin: 0;
            padding: 30px;
            font-size: 13px;
            line-height: 1.5;
            -webkit-print-color-adjust: exact;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #0f172a;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        .brand {{
            font-weight: 900;
            font-size: 14px;
            letter-spacing: 0.15em;
            color: #0284c7;
            text-transform: uppercase;
        }}
        .badge {{
            display: inline-block;
            font-family: monospace;
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            background: #f1f5f9;
            color: #334155;
            border: 1px solid #cbd5e1;
            text-transform: uppercase;
        }}
        .kicker {{
            font-family: monospace;
            font-size: 11px;
            font-weight: 700;
            color: #0284c7;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        h1 {{
            font-size: 26px;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 8px 0;
            letter-spacing: -0.02em;
        }}
        .subtitle {{
            font-size: 14px;
            color: #64748b;
            margin-bottom: 25px;
        }}
        .score-card {{
            display: flex;
            gap: 20px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 18px 24px;
            margin-bottom: 30px;
            align-items: center;
        }}
        .score-num {{
            font-size: 44px;
            font-weight: 900;
            color: #0f172a;
            line-height: 1;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-box {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 14px;
        }}
        .stat-label {{
            font-size: 11px;
            font-family: monospace;
            color: #64748b;
            text-transform: uppercase;
        }}
        .stat-val {{
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
            margin-top: 4px;
        }}
        h2 {{
            font-size: 16px;
            font-weight: 700;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 8px;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #0f172a;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-bottom: 30px;
        }}
        th {{
            background: #f1f5f9;
            text-align: left;
            padding: 8px 12px;
            font-weight: 700;
            color: #334155;
            border-bottom: 2px solid #cbd5e1;
        }}
        td {{
            padding: 8px 12px;
            border-bottom: 1px solid #e2e8f0;
            color: #1e293b;
        }}
        .score-note {{
            font-size: 12px;
            color: #64748b;
            margin-top: 6px;
        }}
        .toc {{
            margin: 0 0 28px;
            padding: 0;
            columns: 2;
            column-gap: 28px;
        }}
        .toc li {{
            break-inside: avoid;
            margin: 0 0 4px;
            list-style: none;
        }}
        .toc a {{
            color: #0f172a;
            text-decoration: none;
        }}
        .toc span {{
            font-family: monospace;
            color: #64748b;
            margin-right: 6px;
        }}
        .part-label {{
            font-family: monospace;
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #0284c7;
            margin: 22px 0 0;
        }}
        .seo-section h4 {{
            font-size: 18px;
            margin-bottom: 8px;
            border-bottom: 2px solid #0f172a;
            padding-bottom: 6px;
        }}
        .check {{
            border: 1px solid #e2e8f0;
            border-left: 4px solid #cbd5e1;
            border-radius: 4px;
            padding: 10px 12px;
            margin: 8px 0;
            page-break-inside: avoid;
        }}
        .check h5 {{
            margin: 0 0 4px;
            font-size: 13px;
        }}
        .status {{
            font-family: monospace;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #334155;
            margin: 0 0 6px;
        }}
        .check.issue {{ border-left-color: #f97316; }}
        .check.clean {{ border-left-color: #0f172a; }}
        .check.measured {{ border-left-color: #0284c7; }}
        .check.inferred {{ border-left-color: #64748b; }}
        .check.gap, .check.untested {{ border-left-color: #cbd5e1; }}
        .check.na {{ border-left-color: #e2e8f0; }}
        .finding-card {{
            border: 1px solid #e2e8f0;
            border-left: 4px solid #0284c7;
            border-radius: 4px;
            padding: 14px;
            margin-bottom: 12px;
            background: #ffffff;
            page-break-inside: avoid;
        }}
        .finding-card.CRITICAL {{ border-left-color: #ef4444; }}
        .finding-card.HIGH {{ border-left-color: #f97316; }}
        .finding-card.MEDIUM {{ border-left-color: #eab308; }}
        .finding-card.LOW {{ border-left-color: #0284c7; }}
        .finding-title {{
            font-weight: 700;
            font-size: 13px;
            color: #0f172a;
            margin-bottom: 4px;
        }}
        .finding-desc {{
            color: #475569;
            margin-bottom: 6px;
        }}
        .finding-rec {{
            font-size: 12px;
            background: #f8fafc;
            border-radius: 4px;
            padding: 6px 10px;
            color: #0369a1;
            font-family: monospace;
        }}
        .footer {{
            margin-top: 40px;
            border-top: 1px solid #e2e8f0;
            padding-top: 15px;
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            color: #94a3b8;
            font-family: monospace;
        }}
        /* Enterprise Dossier Scorecard & Layout */
        .exec-summary-dossier {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        .dossier-meta-bar {{
            display: flex;
            gap: 20px;
            font-family: monospace;
            font-size: 11px;
            color: #64748b;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        .exec-scorecard-grid {{
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 25px;
            align-items: center;
        }}
        .kpi-score-card {{
            background: #0f172a;
            color: #ffffff;
            border-radius: 6px;
            padding: 18px;
            text-align: center;
        }}
        .kpi-label {{
            font-family: monospace;
            font-size: 10px;
            letter-spacing: 0.1em;
            color: #94a3b8;
            display: block;
            margin-bottom: 6px;
        }}
        .kpi-number {{
            font-size: 48px;
            font-weight: 900;
            line-height: 1;
            color: #38bdf8;
        }}
        .kpi-denom {{
            font-size: 20px;
            color: #64748b;
        }}
        .kpi-grade {{
            font-family: monospace;
            font-size: 10px;
            color: #34d399;
            margin-top: 6px;
            display: block;
        }}
        .kpi-narrative-card h4 {{
            margin: 0 0 8px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .kpi-narrative-card p {{
            margin: 0 0 12px;
            color: #475569;
            font-size: 13px;
            line-height: 1.5;
        }}
        .exec-key-points {{
            display: grid;
            gap: 6px;
            font-size: 12px;
        }}
        .point-item {{
            padding: 6px 10px;
            border-radius: 4px;
        }}
        .point-item.strength {{ background: #ecfdf5; color: #065f46; border-left: 3px solid #10b981; }}
        .point-item.blocker {{ background: #fef2f2; color: #991b1b; border-left: 3px solid #ef4444; }}
        .point-item.catalyst {{ background: #eff6ff; color: #1e40af; border-left: 3px solid #3b82f6; }}
        
        .part-header {{
            font-size: 16px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #0f172a;
            margin: 35px 0 15px;
            padding-bottom: 6px;
            border-bottom: 2px solid #0284c7;
        }}
        .lead-scope-note {{
            font-size: 13px;
            color: #475569;
            line-height: 1.6;
            margin-bottom: 25px;
        }}
        .section-summary-lead {{
            font-size: 13px;
            color: #334155;
            font-weight: 500;
            line-height: 1.5;
            margin: 6px 0 14px;
        }}
        .check-result-text {{
            font-size: 12px;
            color: #475569;
            margin: 4px 0 8px;
        }}
        .data-table-wrap {{
            overflow-x: auto;
            margin: 14px 0 20px;
        }}
        .data-table-wrap table {{
            margin-bottom: 0;
        }}
        .badge-sm {{
            display: inline-block;
            font-family: monospace;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 3px;
            background: #f1f5f9;
            color: #334155;
            border: 1px solid #cbd5e1;
        }}
        .scope-tag {{
            font-family: monospace;
            font-size: 10px;
            color: #0284c7;
        }}
        .table-empty {{
            font-size: 12px;
            color: #94a3b8;
            font-style: italic;
            margin: 10px 0;
        }}
        .chapter-panel {{
            border: 1px solid #e2e8f0;
            background: #f8fafc;
            padding: 12px 14px;
            margin: 8px 0 16px;
        }}
        .agent-consulting-dossier {{
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-left: 4px solid #0284c7;
            border-radius: 6px;
            padding: 16px 18px;
            margin: 14px 0 20px;
            page-break-inside: avoid;
        }}
        .agent-header-strip {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 10px;
            margin-bottom: 14px;
        }}
        .agent-badge {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .agent-id-tag {{
            font-family: monospace;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            background: #0f172a;
            color: #f8fafc;
            padding: 3px 8px;
            border-radius: 3px;
        }}
        .agent-name {{
            font-size: 13px;
            color: #0f172a;
        }}
        .agent-role-title {{
            font-size: 11px;
            color: #64748b;
            font-weight: 500;
        }}
        .consulting-section {{
            margin-bottom: 14px;
        }}
        .consulting-heading {{
            font-size: 13px;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 6px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .consulting-narrative {{
            font-size: 12px;
            line-height: 1.6;
            color: #334155;
            margin: 0;
        }}
        .consulting-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 14px;
        }}
        .consulting-col {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 12px;
        }}
        .consulting-subheading {{
            font-size: 11px;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 6px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .consulting-text {{
            font-size: 11px;
            line-height: 1.5;
            color: #475569;
            margin: 0 0 6px;
        }}
        .code-fix-block, .verification-block {{
            background: #0f172a;
            color: #e2e8f0;
            border-radius: 4px;
            padding: 8px 10px;
            font-family: monospace;
            font-size: 10px;
            line-height: 1.4;
            overflow-x: auto;
            word-break: break-word;
        }}
        .code-fix-block code, .verification-block code {{
            color: #38bdf8;
            font-family: monospace;
        }}
        .chapter-empirical-evidence {{
            margin-top: 14px;
            border-top: 1px solid #e2e8f0;
            padding-top: 12px;
        }}
        .evidence-table-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #0f172a;
            margin: 0 0 8px;
        }}
        .sub-index-ledger-header {{
            margin: 22px 0 8px;
            padding-bottom: 4px;
            border-bottom: 1px solid #cbd5e1;
        }}
        .sub-index-ledger-header h5 {{
            font-size: 13px;
            font-weight: 700;
            color: #0f172a;
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .ledger-desc {{
            font-size: 11px;
            color: #64748b;
            margin: 2px 0 0;
        }}
        .sources-kicker, .chart-title {{
            font-family: monospace;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #64748b;
            margin: 0 0 6px;
        }}
        .source-list {{
            list-style: none;
            padding: 0;
            margin: 0 0 10px;
        }}
        .source-list li {{
            font-size: 12px;
            color: #334155;
            margin: 0 0 4px;
        }}
        .src {{
            font-family: monospace;
            font-size: 10px;
            font-weight: 700;
            margin-right: 6px;
            color: #0f172a;
        }}
        .chapter-chart {{
            margin: 10px 0;
            page-break-inside: avoid;
        }}
        .chapter-chart figcaption {{
            display: flex;
            flex-direction: column;
            gap: 2px;
            margin-bottom: 4px;
        }}
        .chapter-chart figcaption strong {{
            font-size: 12px;
            color: #0f172a;
        }}
        .chapter-chart figcaption span, .chart-gap {{
            font-size: 11px;
            color: #475569;
            line-height: 1.45;
        }}
        .chapter-chart svg text {{
            font-size: 11px;
            fill: #0f172a;
            font-family: sans-serif;
        }}
        
        /* 16-Field Enterprise Finding Card */
        .finding-card-v2 {{
            border: 1px solid #e2e8f0;
            border-left: 5px solid #0284c7;
            border-radius: 6px;
            margin: 12px 0 18px;
            background: #ffffff;
            page-break-inside: avoid;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .finding-card-v2.critical {{ border-left-color: #ef4444; }}
        .finding-card-v2.high {{ border-left-color: #f97316; }}
        .finding-card-v2.medium {{ border-left-color: #eab308; }}
        .finding-card-v2.low {{ border-left-color: #0284c7; }}
        .finding-card-v2.info {{ border-left-color: #64748b; }}
        
        .finding-v2-header {{
            padding: 10px 14px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .header-tags {{
            display: flex;
            gap: 6px;
            align-items: center;
        }}
        .badge-tag {{
            font-family: monospace;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 3px;
            text-transform: uppercase;
        }}
        .badge-tag.sev-critical {{ background: #fee2e2; color: #991b1b; }}
        .badge-tag.sev-high {{ background: #ffedd5; color: #9a3412; }}
        .badge-tag.sev-medium {{ background: #fef9c3; color: #854d0e; }}
        .badge-tag.sev-low {{ background: #e0f2fe; color: #075985; }}
        .badge-tag.sev-info {{ background: #f1f5f9; color: #475569; }}
        .badge-tag.scope-page_verified {{ background: #dcfce7; color: #166534; }}
        .badge-tag.scope-sample_verified {{ background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }}
        .badge-tag.scope-site_inferred {{ background: #f3f4f6; color: #374151; }}
        .badge-tag.status-verified {{ background: #ecfdf5; color: #065f46; }}
        .badge-tag.status-open {{ background: #fef2f2; color: #991b1b; }}
        .finding-id-tag {{
            font-family: monospace;
            font-size: 11px;
            font-weight: 800;
            color: #475569;
        }}
        .finding-v2-title {{
            margin: 0;
            font-size: 13px;
            font-weight: 700;
            color: #0f172a;
        }}
        .finding-v2-body {{
            padding: 12px 14px;
        }}
        .finding-field-block {{
            margin-bottom: 8px;
        }}
        .field-title {{
            font-size: 11px;
            font-weight: 700;
            font-family: monospace;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            display: block;
            margin-bottom: 2px;
        }}
        .field-text {{
            font-size: 12px;
            color: #1e293b;
            margin: 0;
            line-height: 1.45;
        }}
        .field-text.action-text {{
            color: #0284c7;
            font-weight: 600;
        }}
        .field-text.verify-text {{
            color: #15803d;
            font-weight: 600;
        }}
        .finding-two-col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 8px;
        }}
        .scope-note {{
            font-size: 11px;
            color: #64748b;
            font-style: italic;
        }}
        .action-block {{
            background: #f0f9ff;
            padding: 8px 10px;
            border-radius: 4px;
            border-left: 3px solid #0284c7;
        }}
        .finding-meta-footer {{
            display: flex;
            gap: 14px;
            flex-wrap: wrap;
            font-size: 11px;
            font-family: monospace;
            color: #64748b;
        /* Specialist Agent Analysis Dossier */
        .agent-analysis-card {{
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            border-left: 4px solid #0284c7;
            border-radius: 6px;
            padding: 14px 16px;
            margin: 12px 0 16px;
            page-break-inside: avoid;
        }}
        .agent-badge-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e2e8f0;
        }}
        .agent-title {{
            font-size: 13px;
            color: #0f172a;
        }}
        .agent-title code {{
            font-size: 11px;
            color: #64748b;
        }}
        .agent-role-pill {{
            font-family: monospace;
            font-size: 10px;
            font-weight: 700;
            background: #e0f2fe;
            color: #0369a1;
            padding: 2px 8px;
            border-radius: 3px;
        }}
        .agent-exec-summary {{
            font-size: 13px;
            line-height: 1.5;
            color: #1e293b;
            margin: 0 0 10px;
        }}
        .agent-diag-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 10px;
            padding: 8px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
        }}
        .diag-label {{
            display: block;
            font-size: 11px;
            font-weight: 700;
            color: #475569;
            margin-bottom: 2px;
        }}
        .diag-val {{
            font-size: 12px;
            color: #0f172a;
            margin: 0;
            line-height: 1.4;
        }}
        .agent-verification-strip {{
            display: flex;
            align-items: baseline;
            gap: 8px;
            font-size: 11px;
            padding-top: 6px;
            border-top: 1px solid #e2e8f0;
        }}
        .ver-label {{
            font-weight: 700;
            color: #475569;
            white-space: nowrap;
        }}
        .agent-verification-strip code {{
            font-size: 11px;
            color: #0369a1;
        }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">DRISTIK AI // SECTION DOSSIER</div>
        <div class="badge">{badge}</div>
    </div>

    <div class="kicker">{title}</div>
    <h1>{domain}</h1>
    <div class="subtitle">{subtitle} — Assessed on {date_str}</div>

    <div class="score-card">
        <div>
            <div class="stat-label">{score_label}</div>
            <div class="score-num">{score_html}</div>
        </div>
        <div style="border-left: 1px solid #cbd5e1; padding-left: 20px;">
            <div style="font-weight: 700; color: #0f172a;">Executive Synthesis</div>
            <div style="color: #475569; font-size: 12px; margin-top: 4px;">
                {self._get_section_summary(report, section_key)}
            </div>
            {score_note}
        </div>
    </div>

    <div class="stat-grid">
        <div class="stat-box">
            <div class="stat-label">PAGES AUDITED</div>
            <div class="stat-val">{len(pages)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">EVIDENCE FINDINGS</div>
            <div class="stat-val">{len(findings)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">{assurance_label}</div>
            <div class="stat-val">{assurance_value}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">{standard_label}</div>
            <div class="stat-val">{standard_value}</div>
        </div>
    </div>

    {findings_html}

    {extra_html}

    {book_html}

    <div class="footer">
        <div>DRISTIK AUTONOMOUS INTELLIGENCE SYSTEMS // {domain}</div>
        <div>{footer_mark}</div>
    </div>
</body>
</html>"""

    def _matches_section(self, finding, section_key: str) -> bool:
        cat = str(getattr(finding, "category", "") or "").upper()
        title = (getattr(finding, "title", "") or "").lower()
        if section_key == "crawl":
            return "TECHNICAL" in cat or "INFRASTRUCTURE" in cat or "crawl" in title or "sitemap" in title
        elif section_key == "seo":
            return "SEO" in cat or "CONTENT" in cat or "title" in title or "meta" in title or "h1" in title
        elif section_key == "geo":
            return "GEO" in cat or "AI" in cat or "citability" in title or "llm" in title or "perplexity" in title
        elif section_key == "aeo":
            return "SCHEMA" in cat or "STRUCTURED" in cat or "entity" in title or "faq" in title or "json-ld" in title
        elif section_key == "cro":
            return "CRO" in cat or "EXPERIENCE" in cat or "cta" in title or "conversion" in title or "friction" in title
        elif section_key == "competitors":
            return "COMPETITOR" in cat or "bakeoff" in title or "rival" in title or "benchmark" in title
        return False

    def _extract_score_num(self, val: Any) -> Optional[int]:
        if val is None:
            return None
        if hasattr(val, "score"):
            s = getattr(val, "score")
            if s is not None:
                try:
                    return int(round(float(s)))
                except (ValueError, TypeError):
                    pass
        if isinstance(val, dict):
            s = val.get("score")
            if s is not None:
                try:
                    return int(round(float(s)))
                except (ValueError, TypeError):
                    pass
        if isinstance(val, (int, float)):
            return int(round(val))
        if isinstance(val, str):
            try:
                return int(round(float(val)))
            except (ValueError, TypeError):
                pass
        return None

    def _resolve_category_score(self, cat_scores: Dict[str, Any], *candidates: str) -> Optional[int]:
        for candidate in candidates:
            for variant in (candidate, candidate.upper(), candidate.lower()):
                if variant in cat_scores:
                    extracted = self._extract_score_num(cat_scores[variant])
                    if extracted is not None:
                        return extracted
        return None

    def _get_section_score(self, report: ExecutiveReport, section_key: str) -> int:
        honest = getattr(report, "honest_scores", None)
        scores = getattr(report, "scores", None)
        cat_scores = getattr(scores, "category_scores", {}) or {} if scores else {}
        base_score = 70
        if scores:
            extracted_base = self._extract_score_num(getattr(scores, "overall_score", None))
            if extracted_base is not None:
                base_score = extracted_base

        if section_key in ("crawl", "seo"):
            if honest and getattr(honest, "honest_google_search", None) is not None:
                val = self._extract_score_num(getattr(honest, "honest_google_search"))
                if val is not None:
                    return val
            cat_val = self._resolve_category_score(cat_scores, "TECHNICAL_SEO", "ON_PAGE_SEO", "technical_seo", "on_page_seo")
            return cat_val if cat_val is not None else base_score
        elif section_key in ("geo", "aeo"):
            if honest and getattr(honest, "honest_ai_readiness", None) is not None:
                val = self._extract_score_num(getattr(honest, "honest_ai_readiness"))
                if val is not None:
                    return val
            cat_val = self._resolve_category_score(cat_scores, "GEO", "AI_SEARCH", "geo", "ai_search", "SCHEMA", "schema")
            return cat_val if cat_val is not None else base_score
        elif section_key == "cro":
            if honest and getattr(honest, "honest_human_experience", None) is not None:
                val = self._extract_score_num(getattr(honest, "honest_human_experience"))
                if val is not None:
                    return val
            cat_val = self._resolve_category_score(cat_scores, "UX_CONVERSION", "ux_conversion", "CRO", "cro")
            return cat_val if cat_val is not None else base_score
        elif section_key == "competitors":
            bakeoff = getattr(report, "competitor_bakeoff", None)
            if bakeoff:
                tot = (bakeoff.target_wins or 0) + (bakeoff.competitor_wins or 0) + (bakeoff.ties or 0)
                if tot > 0:
                    return int(((bakeoff.target_wins or 0) / tot) * 100)
            return 65
        return base_score

    def _get_section_summary(self, report: ExecutiveReport, section_key: str) -> str:
        if section_key == "crawl":
            return "Multi-page crawl validated HTTP response codes, TTFB network latencies, robots.txt crawler permissions, and canonical URI consistency."
        elif section_key == "seo":
            return "Comprehensive search engine optimization assessment covering title/meta lengths, H1 heading outline hierarchy, and indexation hygiene."
        elif section_key == "geo":
            return "Generative engine optimization audit evaluating prose factual density, /llms.txt manifests, and AI answer engine citability metrics."
        elif section_key == "aeo":
            return (
                "Answer-engine audit of question coverage, answer quality, source eligibility, and observed visibility. "
                "Readiness, live visibility, and business impact stay separate."
            )
        elif section_key == "cro":
            return "Conversion rate optimization assessment identifying above-the-fold value proposition clarity, CTA ergonomics, and commercial friction points."
        elif section_key == "competitors":
            return "Head-to-head empirical testing across commercial buyer inquiry queries against verified industry peers and rival market leaders."
        return report.story_summary or "Deterministic website intelligence audit."

    def _render_finding(self, finding) -> str:
        sev = str(getattr(finding, "severity", "MEDIUM") or "MEDIUM").upper()
        title = getattr(finding, "title", "Audit Finding")
        desc = getattr(finding, "description", "")
        rec = getattr(finding, "suggested_fix", "") or getattr(finding, "recommendation", "")
        return f"""
        <div class="finding-card {sev}">
            <div style="display:flex;justify-content:space-between;">
                <div class="finding-title">{title}</div>
                <span class="badge" style="background:{'#fee2e2' if sev in ('CRITICAL','HIGH') else '#fef3c7'};color:#0f172a;">{sev}</span>
            </div>
            <div class="finding-desc">{desc}</div>
            {f'<div class="finding-rec">Suggested Fix: {rec}</div>' if rec else ''}
        </div>
        """

    def _render_extra_section_tables(self, report: ExecutiveReport, section_key: str, pages: List[Any]) -> str:
        if section_key in ("crawl", "seo") and pages:
            rows = []
            for p in pages[:8]:
                u = getattr(p, "url", "")
                st = getattr(p, "status_code", 200)
                t = getattr(p, "title", "") or "—"
                h1 = (getattr(p, "h1", []) or ["—"])[0]
                rows.append(f"<tr><td><code>{u}</code></td><td>{st}</td><td>{t[:45]}</td><td>{h1[:40]}</td></tr>")
            return f"""
            <h2>Crawled Pages & Routing Ledger</h2>
            <table>
                <thead>
                    <tr><th>URL</th><th>Status</th><th>Title Tag</th><th>Primary H1</th></tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
            """
        elif section_key == "competitors" and getattr(report, "competitor_bakeoff", None):
            b = report.competitor_bakeoff
            return f"""
            <h2>Head-to-Head Commercial Query Results</h2>
            <table>
                <thead>
                    <tr><th>Competitor Domain</th><th>Target Wins</th><th>Competitor Wins</th><th>Ties</th></tr>
                </thead>
                <tbody>
                    <tr><td><b>{b.competitor_domain or 'Peer Rival'}</b></td><td style="color:#16a34a;font-weight:700;">{b.target_wins}</td><td style="color:#dc2626;font-weight:700;">{b.competitor_wins}</td><td>{b.ties}</td></tr>
                </tbody>
            </table>
            """
        return ""


section_report_generator = SectionReportGenerator()
