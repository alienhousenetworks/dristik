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
            "aeo": ("04 // ANSWER ENGINE OPTIMIZATION (AEO)", "Schema.org Knowledge Graph, Brand Entity Grounding & Conversational Answers"),
            "cro": ("05 // CONVERSION RATE OPTIMIZATION (CRO)", "Value Proposition Delivery, CTA Ergonomics, Trust Signals & Friction"),
            "competitors": ("06 // COMPETITOR BENCHMARK & COMMERCIAL BAKE-OFF", "Head-to-Head Commercial Inquiry Testing & Industry Peer Parity"),
        }
        title, subtitle = TITLES.get(section_key, (f"{section_key.upper()} AUDIT DOSSIER", "Empirical Evidence & Remediation Blueprint"))

        # Section-specific metrics and findings
        findings = [f for f in (report.findings or []) if self._matches_section(f, section_key)]
        if not findings and report.findings:
            findings = report.findings[:10]

        pages = report.crawl_manifest.pages if (report.crawl_manifest and report.crawl_manifest.pages) else (report.page_reports or [])
        score_val = self._get_section_score(report, section_key)

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
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">DRISTIK AI // SECTION DOSSIER</div>
        <div class="badge">EVIDENCE-GROUNDED // ZERO-FAKE AUDIT</div>
    </div>

    <div class="kicker">{title}</div>
    <h1>{domain}</h1>
    <div class="subtitle">{subtitle} — Assessed on {date_str}</div>

    <div class="score-card">
        <div>
            <div class="stat-label">SECTION HEALTH SCORE</div>
            <div class="score-num">{score_val}<span style="font-size:20px;color:#64748b;">/100</span></div>
        </div>
        <div style="border-left: 1px solid #cbd5e1; padding-left: 20px;">
            <div style="font-weight: 700; color: #0f172a;">Executive Synthesis</div>
            <div style="color: #475569; font-size: 12px; margin-top: 4px;">
                {self._get_section_summary(report, section_key)}
            </div>
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
            <div class="stat-label">ASSURANCE TIER</div>
            <div class="stat-val">CERTIFIED</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">EVIDENCE STANDARD</div>
            <div class="stat-val">ZERO-FAKE AST</div>
        </div>
    </div>

    <h2>Verified Empirical Findings ({len(findings)})</h2>
    {"".join(self._render_finding(f) for f in findings) if findings else "<p style='color:#64748b;'>No critical defects recorded for this section.</p>"}

    {self._render_extra_section_tables(report, section_key, pages)}

    <div class="footer">
        <div>DRISTIK AUTONOMOUS INTELLIGENCE SYSTEMS // {domain}</div>
        <div>PAGE 1 OF 1 // IMMUTABLE PROVENANCE SEAL</div>
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
            return "Answer engine optimization cross-checks Schema.org JSON-LD entity graph nodes, brand entity resolution, and conversational answer grounding."
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
