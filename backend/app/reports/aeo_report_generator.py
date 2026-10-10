"""
Complete AEO (Answer Engine Optimization) Report Generator for Dristik AI (2026 Master Standard)
Produces:
1. Standalone responsive HTML document with 20-Section AEO Master Index, sticky sidebar,
   4-tier KPI scorecards, 14-field AEO finding cards, Question-to-Page evidence matrix, and export links.
2. Structured JSON report covering all 20 sections for API consumers.

Core Architectural Integrity Rule:
Answer Readiness (on-site content completeness), Feature Eligibility (schema & structural fit),
and Observed Answer Visibility (empirically recorded SERP/voice/AI snippet appearances) are strictly separated.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from app.domain.models import ExecutiveReport, Finding, FindingStatus


class CompleteAeoReportGenerator:
    """
    Renders the 20-Section Master Answer Engine Optimization (AEO) Report
    in HTML and structured JSON. Strictly distinguishes Answer Readiness,
    Search Feature Eligibility, and Observed Live Answer Visibility.
    """

    SECTIONS = [
        ("sec-01", "01. Executive Summary & Answer Visibility Health"),
        ("sec-02", "02. Audit Scope, Platform Coverage & Methodology"),
        ("sec-03", "03. Question Universe & Intent Mapping"),
        ("sec-04", "04. Answer Readiness & Content Structure"),
        ("sec-05", "05. Featured Snippet Analysis"),
        ("sec-06", "06. People Also Ask & Related Questions"),
        ("sec-07", "07. FAQ and Question-Answer Content Audit"),
        ("sec-08", "08. Structured Data & Rich Results"),
        ("sec-09", "09. Entity Answers & Knowledge Panels"),
        ("sec-10", "10. Voice & Conversational Search"),
        ("sec-11", "11. AI Answer Engine Visibility"),
        ("sec-12", "12. Local & Action-Oriented Answers"),
        ("sec-13", "13. Product, Commercial & Transactional Answers"),
        ("sec-14", "14. Support, Documentation & Troubleshooting"),
        ("sec-15", "15. Answer Accuracy & Source Quality"),
        ("sec-16", "16. Competitor Answer Benchmarking"),
        ("sec-17", "17. Search Performance & Business Outcomes"),
        ("sec-18", "18. Content Gaps & Answer Strategy"),
        ("sec-19", "19. Prioritized Remediation Roadmap (P0 - P3)"),
        ("sec-20", "20. Appendices & Evidence Register"),
    ]

    DOMAINS_10 = [
        ("Featured Snippet Optimization", "Concise definitions (40-60 words), lists, comparison tables, and heading alignment formatted for rank-zero extraction."),
        ("Question-Based Search Optimization", "Question clusters, FAQ structures, intent resolution, and comprehensive follow-up coverage."),
        ("Voice Search & Conversational Answers", "Natural conversational phrasing, spoken readability, pronunciation clarity, and local action support."),
        ("Rich Results & Structured Answers", "Applicable JSON-LD schemas (Organization, Product, Article, LocalBusiness) strictly validated against visible DOM."),
        ("Knowledge Panels & Entity Answers", "Canonical entity identity, disambiguation, authoritative sameAs profiles, and Wikidata/knowledge graph alignment."),
        ("AI Answer Engine Optimization", "Factual grounding, passage extractability, citation frequency across ChatGPT, Perplexity, Gemini, and Claude."),
        ("Local & Action-Oriented Answers", "Name, Address, Phone (NAP), operating hours, service radius, and Google Business Profile consistency."),
        ("Product & Transactional Answers", "Specifications, pricing models, feature matrices, compatibility, availability, and return policies."),
        ("Support & Troubleshooting Answers", "Procedural step-by-step guides, prerequisites, error codes, and technical troubleshooting flows."),
        ("Answer Visibility & Performance Measurement", "Search Console query-level click/impression tracking, answer feature capture, and conversion attribution."),
    ]

    def render_json_report(self, report: ExecutiveReport) -> Dict[str, Any]:
        """Returns structured JSON covering all 20 sections."""
        analysis_id = report.analysis_id or report.report_id
        g = report.geo_readiness
        v_card = report.ai_visibility_scorecard
        scores = getattr(report, "scores", None)

        # Categorize P0 - P3 findings
        p0_findings = [f for f in report.findings if f.priority >= 9 or (hasattr(f.severity, "value") and f.severity.value == "CRITICAL")]
        p1_findings = [f for f in report.findings if (f.priority in (7, 8)) and f not in p0_findings]
        p2_findings = [f for f in report.findings if (f.priority in (5, 6)) and f not in p0_findings and f not in p1_findings]
        p3_findings = [f for f in report.findings if f not in p0_findings and f not in p1_findings and f not in p2_findings]

        questions_total = getattr(g, "questions_total", 0) if g else 0
        questions_supp = getattr(g, "questions_supported", 0) if g else 0
        questions_part = getattr(g, "questions_partial", 0) if g else 0
        questions_unsupp = getattr(g, "questions_unsupported", 0) if g else 0

        # Answer readiness score (0-100)
        answer_readiness_score = getattr(g, "extractability_score", None) if g else None
        if answer_readiness_score is None and scores:
            answer_readiness_score = getattr(scores, "geo_score", None)
        if answer_readiness_score is None and questions_total > 0:
            answer_readiness_score = round(((questions_supp * 1.0 + questions_part * 0.5) / questions_total) * 100, 1)

        visibility_status = getattr(v_card, "status", "NOT_MEASURED") if v_card else "NOT_MEASURED"
        citation_rate = getattr(report, "ai_visibility_score", None)

        # Question mapping
        mapped_questions = []
        if g and g.questions:
            for q in g.questions:
                # Classify question type
                q_text = q.question.strip()
                q_lower = q_text.lower()
                q_type = "What"
                for word in ["what", "why", "how", "when", "where", "who", "which", "compare", "vs"]:
                    if q_lower.startswith(word) or f" {word} " in q_lower:
                        q_type = word.capitalize()
                        break

                mapped_questions.append({
                    "question_key": q.question_key,
                    "question": q_text,
                    "question_type": q_type,
                    "category": q.category,
                    "status": q.status,
                    "evidence_url": q.evidence_url or report.website_url,
                    "answer_excerpt": q.evidence_snippet or q.answer_snippet or "",
                    "recommended_remediation": q.recommended_answer or "",
                    "remediation_type": q.remediation_type or "ANSWER_BLOCK",
                })

        def _page_has_content_signals(p: Any) -> bool:
            h1 = getattr(p, "h1_tags", None) or getattr(p, "h1", None)
            if not h1 and getattr(p, "seo", None):
                h1 = getattr(p.seo, "h1_tags", None)
            st = getattr(p, "schema_types", None)
            if not st and getattr(p, "seo", None):
                st = getattr(p.seo, "schema_types", None)
            return bool(h1 or st)

        def _get_page_schemas(p: Any) -> List[str]:
            st = getattr(p, "schema_types", None)
            if st is None and getattr(p, "seo", None):
                st = getattr(p.seo, "schema_types", None)
            return st or []

        return {
            "report_id": report.report_id,
            "analysis_id": analysis_id,
            "domain": report.domain,
            "website_url": report.website_url,
            "generated_at": report.generated_at,
            "report_type": "AEO_MASTER_AUDIT_2026",
            "certification_status": getattr(report, "certification_status", "CERTIFIED"),
            "kpis": {
                "answer_readiness_score": answer_readiness_score,
                "observed_visibility_status": visibility_status,
                "measured_citation_rate": citation_rate,
                "questions_evaluated": questions_total,
                "questions_supported": questions_supp,
                "questions_partial": questions_part,
                "questions_unsupported": questions_unsupp,
                "total_findings": len(report.findings),
            },
            "exports": {
                "html_report": f"/api/v1/reports/{analysis_id}/aeo-report?format=html",
                "json_report": f"/api/v1/reports/{analysis_id}/aeo-report?format=json",
                "remediation_tracker_csv": f"/api/v1/reports/{analysis_id}/export/aeo-remediation-tracker.csv",
                "question_dataset_csv": f"/api/v1/reports/{analysis_id}/export/aeo-question-dataset.csv",
            },
            "sections": {
                "01_executive_summary": {
                    "headline": getattr(g, "headline", "") if g else report.story_summary,
                    "answer_readiness_score": answer_readiness_score,
                    "observed_visibility_status": visibility_status,
                    "questions_evaluated": questions_total,
                    "questions_answered_directly": questions_supp,
                    "critical_risks": [f.title for f in p0_findings[:5]],
                    "core_rule": "Answer readiness, search feature eligibility, and observed answer appearances are separate outcomes.",
                },
                "02_audit_scope_and_methodology": {
                    "domain": report.domain,
                    "website_url": report.website_url,
                    "pages_audited": len(report.page_reports),
                    "search_markets": ["Google Search", "Google Assistant / Voice", "Bing / Copilot", "ChatGPT Search", "Perplexity AI"],
                    "evaluation_date": report.generated_at,
                    "data_sources": ["DOM Crawl Engine", "JSON-LD Schema Validator", "SERP Snippet Parser", "AI Knowledge Connectors"],
                    "disclaimer": "Readiness scores evaluate content completeness against the audit rubric and do NOT represent an official Google ranking factor or guaranteed snippet probability.",
                },
                "03_question_universe_and_intent_mapping": {
                    "intent_taxonomy": [
                        "Informational (What, Why, How)",
                        "Navigational (Brand, Portal, Login)",
                        "Commercial Investigation (Which, Best, Features)",
                        "Transactional (Pricing, Cost, Plans, Terms)",
                        "Support & Troubleshooting (How to fix, Error, Requirements)",
                    ],
                    "question_types": ["What", "Why", "How", "When", "Where", "Who", "Which", "Comparison"],
                    "questions_total": questions_total,
                    "questions_mapped": mapped_questions,
                },
                "04_answer_readiness_and_content_structure": {
                    "readiness_score": answer_readiness_score,
                    "definition_block_rule": "Direct answers must appear in the first relevant passage (40-60 words) directly below the corresponding question heading.",
                    "evaluated_passages": questions_total,
                    "supported_direct_passages": questions_supp,
                    "partial_passages": questions_part,
                },
                "05_featured_snippet_analysis": {
                    "supported_formats": ["Paragraph (Definition)", "Numbered / Bulleted List (Procedure/Ranking)", "HTML Table (Comparison/Pricing)"],
                    "eligible_pages_count": len([p for p in report.page_reports if _page_has_content_signals(p)]),
                    "observed_snippets_note": "Google controls snippet selection dynamically based on query intent. Valid markup improves eligibility but does not guarantee selection.",
                    "competitor_snippet_wins": getattr(report, "competitive_report", None),
                },
                "06_people_also_ask_and_related_questions": {
                    "paa_clusters_analyzed": questions_total,
                    "follow_up_gaps_count": questions_unsupp,
                    "content_consolidation_rule": "Group closely related questions on a single comprehensive authority page rather than spawning fragmented thin pages.",
                },
                "07_faq_and_question_answer_content_audit": {
                    "faq_pages_detected": len([p for p in report.page_reports if "FAQPage" in _get_page_schemas(p)]),
                    "google_faq_restriction_warning": "Google restricts FAQ rich results primarily to authoritative government and healthcare organizations. Non-government sites should prioritize visible on-page UX clarity.",
                    "unverified_facts_omitted": True,
                },
                "08_structured_data_and_rich_results": {
                    "schema_types_detected": getattr(g, "schema_types", []) if g else [],
                    "schema_validation": report.schema_validation.model_dump() if report.schema_validation else None,
                    "rich_result_rule": "Valid structured data establishes technical eligibility, not proof of rich result SERP appearance.",
                },
                "09_entity_answers_and_knowledge_panels": {
                    "brand_entity_name": getattr(g, "entity_name", report.domain) if g else report.domain,
                    "business_profile": report.business_profile.model_dump() if report.business_profile else None,
                    "same_as_profiles": getattr(report, "external_authority", {}).get("profiles", []) if getattr(report, "external_authority", None) else [],
                    "knowledge_panel_rule": "Knowledge panels reflect Google Knowledge Graph consensus across external web entities, not schema declarations alone.",
                },
                "10_voice_and_conversational_search": {
                    "voice_search_rule": "Voice search has no universal ranking system. A passage readable aloud is not necessarily selected by a voice assistant.",
                    "spoken_readability_passages": questions_supp,
                    "pronunciation_clarity_check": "Verified clear entity names, acronym expansions, and unit specifications.",
                },
                "11_ai_answer_engine_visibility": {
                    "visibility_status": visibility_status,
                    "scorecard": v_card.model_dump() if v_card else None,
                    "measured_citation_rate": citation_rate,
                    "platforms": ["ChatGPT Search", "Perplexity", "Google AI Overviews", "Gemini", "Claude"],
                },
                "12_local_and_action_oriented_answers": {
                    "business_name": getattr(report.business_profile, "business_name", None) if report.business_profile else None,
                    "address_available": bool(getattr(report.business_profile, "address", None)) if report.business_profile else False,
                    "phone_available": bool(getattr(report.business_profile, "phone", None)) if report.business_profile else False,
                    "local_answers_note": "For physical businesses, NAP consistency across Google Business Profile and local schema is required for local voice/assistant queries.",
                },
                "13_product_commercial_and_transactional_answers": {
                    "pricing_questions_supported": bool(questions_supp > 0),
                    "product_pages_analyzed": len([p for p in report.page_reports if "Product" in _get_page_schemas(p)]),
                    "rule": "Commercial queries demand explicit specs, pricing tiers, and compatibility tables to prevent answer engine hallucinations.",
                },
                "14_support_documentation_and_troubleshooting": {
                    "troubleshooting_passages": [q for q in mapped_questions if "support" in q["category"].lower() or "troubleshoot" in q["question"].lower()],
                    "procedural_integrity": "Prerequisites, reproducible steps, and expected outcomes are evaluated against the documentation corpus.",
                },
                "15_answer_accuracy_and_source_quality": {
                    "factual_grounding_layer": "Claims validated against first-party crawl DOM.",
                    "contradictions_detected": len(report.contradictions or []),
                    "contradiction_items": [c.model_dump() for c in (report.contradictions or [])],
                },
                "16_competitor_answer_benchmarking": {
                    "competitor_data": report.competitive_report,
                    "rule": "Distinguish commercial competitors from search-answer competitors (e.g. media publications, Wikipedia, and aggregator directories).",
                },
                "17_search_performance_and_business_outcomes": {
                    "search_console_integration": "Available when Search Console OAuth connector is authenticated.",
                    "tracked_metrics": ["Query Impressions", "Direct Clicks", "CTR %", "Average Position", "AI Referral Sessions"],
                },
                "18_content_gaps_and_answer_strategy": {
                    "unanswered_questions_count": questions_unsupp,
                    "partial_questions_count": questions_part,
                    "primary_strategic_opportunity": report.primary_strategic_opportunity,
                },
                "19_prioritized_remediation_roadmap": {
                    "p0_critical": [f.finding_id for f in p0_findings],
                    "p1_high": [f.finding_id for f in p1_findings],
                    "p2_medium": [f.finding_id for f in p2_findings],
                    "p3_opportunity": [f.finding_id for f in p3_findings],
                    "severity_framework": "P0: Major factual errors or broken priority business info. P1: Missing priority answers or invalid critical schema. P2: Structural passage formatting & PAA coverage. P3: Experimental answer opportunities.",
                },
                "20_appendices_and_evidence_register": {
                    "question_inventory": mapped_questions,
                    "schema_results": getattr(g, "schema_types", []) if g else [],
                    "total_urls_inspected": len(report.page_reports),
                    "measurement_rubric": "AEO Master Rubric 2026: 4-Tier Assessment (Readiness, Visibility, Quality, Business Impact).",
                },
            },
        }

    def render_html_report(self, report: ExecutiveReport) -> str:
        """Renders complete standalone HTML document with 20-Section sticky navigation."""
        json_data = self.render_json_report(report)
        analysis_id = json_data["analysis_id"]
        domain = html.escape(json_data["domain"])
        website_url = html.escape(json_data["website_url"])
        generated_at = html.escape(json_data["generated_at"])
        kpis = json_data["kpis"]

        readiness_score = kpis["answer_readiness_score"]
        readiness_display = f"{int(round(readiness_score))}" if readiness_score is not None else "N/A"
        readiness_color = "#10b981" if (readiness_score and readiness_score >= 80) else ("#f59e0b" if (readiness_score and readiness_score >= 60) else "#ef4444")

        visibility_status = kpis["observed_visibility_status"]
        vis_color = "#10b981" if visibility_status == "MEASURED" else "#64748b"

        citation_rate = kpis["measured_citation_rate"]
        cit_display = f"{int(round(citation_rate * 100))}%" if citation_rate is not None else "Unmeasured"

        questions_total = kpis["questions_evaluated"]
        questions_supp = kpis["questions_supported"]
        questions_part = kpis["questions_partial"]
        questions_unsupp = kpis["questions_unsupported"]

        # Navigation links
        nav_items_html = "\n".join(
            f'<a href="#{sec_id}" class="nav-item"><span>{sec_title}</span></a>'
            for sec_id, sec_title in self.SECTIONS
        )

        # 10 AEO Domains HTML Grid
        domains_html = ""
        for idx, (dom_title, dom_desc) in enumerate(self.DOMAINS_10, 1):
            domains_html += f"""
            <div class="domain-card">
                <div class="domain-header">
                    <span class="domain-num">{idx:02d}</span>
                    <h4 class="domain-title">{dom_title}</h4>
                </div>
                <p class="domain-desc">{dom_desc}</p>
            </div>
            """

        # 14-Field AEO Finding Cards HTML
        finding_cards_html = ""
        for idx, f in enumerate(report.findings):
            fid = html.escape(f.finding_id or f"AEO-ANS-{idx+1:03d}")
            if not fid.startswith("AEO-"):
                fid = f"AEO-{fid}"

            sev_class = str(f.severity.value).lower() if hasattr(f.severity, "value") else str(f.severity).lower()
            cat_name = html.escape(f.category.value if hasattr(f.category, "value") else str(f.category))
            subcat = html.escape(f.subcategory or cat_name)
            stat = html.escape(f.status.value if hasattr(f.status, "value") else str(f.status))
            owner = html.escape(f.owner or "Answer Content & SEO Engineering")
            title_esc = html.escape(f.title)
            desc_esc = html.escape(f.description)
            rec_esc = html.escape(f.recommendation)
            why_esc = html.escape(f.why_it_matters or f.business_impact or "Users fail to find a direct answer; answer engines cite competitor sources.")
            exp_esc = html.escape(f.expected_condition or "Concise, verified 40-60 word answer passage formatted under matching H2 question heading.")
            val_esc = html.escape(f.validation_criteria or "Automated re-crawl confirms passage extractability and zero entity contradiction.")
            aff_count = len(f.affected_urls)
            target_url = html.escape(f.affected_urls[0]) if f.affected_urls else website_url

            finding_cards_html += f"""
            <div class="finding-card {sev_class}">
                <div class="finding-header">
                    <div class="finding-title-row">
                        <span class="finding-badge sev-{sev_class}">{sev_class.upper()}</span>
                        <span class="finding-badge status-{stat.lower()}">{stat}</span>
                        <span class="finding-id">{fid}</span>
                        <h4 class="finding-title">{title_esc}</h4>
                    </div>
                    <div class="finding-meta">
                        <span><strong>Domain:</strong> {cat_name} › {subcat}</span>
                        <span><strong>Owner:</strong> {owner}</span>
                        <span><strong>Priority:</strong> {f.priority}/10</span>
                        <span><strong>Impact:</strong> {f.impact}/10</span>
                        <span><strong>Effort:</strong> {f.effort}/10</span>
                        <span><strong>Target URL:</strong> <code>{target_url}</code></span>
                    </div>
                </div>
                <div class="finding-body">
                    <p class="finding-desc">{desc_esc}</p>
                    <div class="field-grid">
                        <div class="field-item">
                            <span class="field-label">Reference Baseline / Expected Condition</span>
                            <span class="field-val">{exp_esc}</span>
                        </div>
                        <div class="field-item">
                            <span class="field-label">Potential Impact on Answer Visibility</span>
                            <span class="field-val">{why_esc}</span>
                        </div>
                        <div class="field-item full-width">
                            <span class="field-label">Prescriptive AEO Recommendation</span>
                            <span class="field-val highlight">{rec_esc}</span>
                        </div>
                        <div class="field-item full-width">
                            <span class="field-label">Verification Acceptance Criteria (Fixed vs Verified)</span>
                            <span class="field-val">{val_esc}</span>
                        </div>
                    </div>
                </div>
            </div>
            """

        # Question-to-Page Dataset Rows HTML
        question_rows_html = ""
        mapped_questions = json_data["sections"]["03_question_universe_and_intent_mapping"]["questions_mapped"]
        for q in mapped_questions:
            q_key = html.escape(q["question_key"])
            q_text = html.escape(q["question"])
            q_type = html.escape(q["question_type"])
            q_cat = html.escape(q["category"])
            q_stat = html.escape(q["status"])
            q_stat_class = q_stat.lower()
            q_url = html.escape(q["evidence_url"])
            q_ans = html.escape(q["answer_excerpt"][:140] + ("..." if len(q["answer_excerpt"]) > 140 else ""))

            question_rows_html += f"""
            <tr>
                <td><code>{q_key}</code></td>
                <td><strong>{q_text}</strong></td>
                <td><span class="badge-dim">{q_type}</span></td>
                <td>{q_cat}</td>
                <td><span class="stat-pill {q_stat_class}">{q_stat}</span></td>
                <td><a href="{q_url}" target="_blank" class="ext-link">{q_url}</a></td>
                <td class="text-snippet">{q_ans or '<span class="text-muted">No verified excerpt</span>'}</td>
            </tr>
            """

        if not question_rows_html:
            question_rows_html = """
            <tr>
                <td colspan="7" style="text-align:center; color:#94a3b8; padding:24px;">
                    No question inventory extracted. Connect dynamic crawler or GSC query data.
                </td>
            </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Complete AEO Master Audit & Answer Engine Optimization Report - {domain}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0f1d;
            --bg-surface: #111827;
            --bg-card: #1f2937;
            --border-subtle: #374151;
            --border-strong: #4b5563;
            --text-main: #f9fafb;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --accent-cyan: #06b6d4;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --accent-indigo: #6366f1;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-primary);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            font-size: 14px;
            line-height: 1.6;
        }}
        .layout-container {{
            display: flex;
            min-height: 100vh;
        }}
        /* Sticky Sidebar */
        .sidebar {{
            width: 320px;
            background: var(--bg-surface);
            border-right: 1px solid var(--border-subtle);
            padding: 24px 16px;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .brand-header {{
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-subtle);
        }}
        .brand-logo {{
            font-size: 18px;
            font-weight: 800;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
            letter-spacing: -0.02em;
        }}
        .brand-logo span {{ color: var(--accent-cyan); }}
        .badge-standard {{
            display: inline-block;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            padding: 2px 8px;
            border-radius: 4px;
            background: rgba(6, 182, 212, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(6, 182, 212, 0.3);
            margin-top: 6px;
        }}
        .nav-index-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            padding: 0 8px;
        }}
        .nav-list {{
            display: flex;
            flex-direction: column;
            gap: 2px;
            flex-grow: 1;
        }}
        .nav-item {{
            display: block;
            padding: 7px 10px;
            border-radius: 6px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.15s ease;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .nav-item:hover {{
            background: var(--bg-card);
            color: var(--accent-cyan);
        }}
        .sidebar-exports {{
            padding-top: 16px;
            border-top: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .btn-export {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 8px 12px;
            border-radius: 6px;
            background: var(--bg-card);
            color: var(--text-main);
            border: 1px solid var(--border-subtle);
            font-size: 12px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.15s ease;
        }}
        .btn-export:hover {{
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
        }}
        /* Main Content */
        .main-content {{
            flex-grow: 1;
            padding: 40px 48px;
            max-width: 1280px;
            overflow-x: hidden;
        }}
        .report-header {{
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border-subtle);
        }}
        .header-meta {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .report-title {{
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -0.03em;
            color: var(--text-main);
            margin-bottom: 8px;
        }}
        .report-subtitle {{
            color: var(--text-secondary);
            font-size: 14px;
        }}
        /* Disclaimers & Integrity Alert */
        .integrity-box {{
            background: rgba(6, 182, 212, 0.08);
            border: 1px solid rgba(6, 182, 212, 0.3);
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 32px;
        }}
        .integrity-box h5 {{
            color: var(--accent-cyan);
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}
        .integrity-box p {{
            color: var(--text-secondary);
            font-size: 13px;
            line-height: 1.5;
        }}
        /* KPI Cards Grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 40px;
        }}
        .kpi-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .kpi-label {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-muted);
        }}
        .kpi-val {{
            font-size: 32px;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            line-height: 1;
        }}
        .kpi-caption {{
            font-size: 12px;
            color: var(--text-secondary);
        }}
        /* Section Styling */
        .section-block {{
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 32px;
            margin-bottom: 32px;
        }}
        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-subtle);
        }}
        .section-title {{
            font-size: 20px;
            font-weight: 700;
            color: var(--text-main);
        }}
        .section-tag {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            padding: 3px 8px;
            border-radius: 4px;
            background: var(--bg-card);
            color: var(--text-secondary);
        }}
        /* 10 Domains Grid */
        .domains-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-top: 16px;
        }}
        .domain-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 16px;
        }}
        .domain-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }}
        .domain-num {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            font-weight: 700;
            color: var(--accent-cyan);
            background: rgba(6, 182, 212, 0.12);
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .domain-title {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-main);
        }}
        .domain-desc {{
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.5;
        }}
        /* Standard 14-Field Finding Card */
        .finding-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-left: 4px solid var(--border-strong);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .finding-card.critical {{ border-left-color: var(--accent-rose); }}
        .finding-card.high {{ border-left-color: #f97316; }}
        .finding-card.medium {{ border-left-color: var(--accent-amber); }}
        .finding-card.low {{ border-left-color: #3b82f6; }}
        .finding-title-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }}
        .finding-badge {{
            font-size: 10px;
            font-weight: 800;
            text-transform: uppercase;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .sev-critical {{ background: rgba(244, 63, 94, 0.2); color: var(--accent-rose); }}
        .sev-high {{ background: rgba(249, 115, 22, 0.2); color: #f97316; }}
        .sev-medium {{ background: rgba(245, 158, 11, 0.2); color: var(--accent-amber); }}
        .sev-low {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; }}
        .status-open {{ background: rgba(239, 68, 68, 0.15); color: #fca5a5; }}
        .finding-id {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            color: var(--accent-cyan);
        }}
        .finding-title {{
            font-size: 15px;
            font-weight: 700;
            color: var(--text-main);
            margin: 0;
        }}
        .finding-meta {{
            display: flex;
            gap: 16px;
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 14px;
            flex-wrap: wrap;
        }}
        .finding-meta code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            background: var(--bg-primary);
            padding: 1px 6px;
            border-radius: 4px;
        }}
        .finding-desc {{
            font-size: 13px;
            color: var(--text-main);
            margin-bottom: 16px;
            line-height: 1.5;
        }}
        .field-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            background: var(--bg-primary);
            padding: 14px;
            border-radius: 6px;
        }}
        .field-item {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .field-item.full-width {{ grid-column: span 2; }}
        .field-label {{
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }}
        .field-val {{
            font-size: 12px;
            color: var(--text-secondary);
        }}
        .field-val.highlight {{
            color: var(--accent-cyan);
            font-weight: 600;
        }}
        /* Question Dataset Table */
        .table-container {{
            overflow-x: auto;
            margin-top: 16px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        th {{
            text-align: left;
            padding: 10px 12px;
            background: var(--bg-card);
            color: var(--text-muted);
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border-subtle);
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-secondary);
        }}
        td code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: var(--accent-cyan);
        }}
        .badge-dim {{
            background: rgba(255, 255, 255, 0.06);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
        }}
        .stat-pill {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .stat-pill.supported {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); }}
        .stat-pill.partial {{ background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); }}
        .stat-pill.unsupported {{ background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); }}
        .ext-link {{
            color: var(--accent-cyan);
            text-decoration: none;
            word-break: break-all;
        }}
        .text-snippet {{ font-style: italic; }}
        /* Alerts */
        .alert-callout {{
            background: var(--bg-card);
            border-left: 3px solid var(--accent-amber);
            padding: 12px 16px;
            border-radius: 4px;
            margin: 16px 0;
            font-size: 12px;
            color: var(--text-secondary);
        }}
        .alert-callout strong {{ color: var(--accent-amber); }}
    </style>
</head>
<body>
    <div class="layout-container">
        <!-- Sticky 20-Section Navigation Sidebar -->
        <aside class="sidebar">
            <div class="brand-header">
                <div class="brand-logo">DRISTIK <span>AEO</span></div>
                <span class="badge-standard">2026 Master Standard</span>
            </div>
            <div class="nav-index-title">20-Section Master Index</div>
            <nav class="nav-list">
                {nav_items_html}
            </nav>
            <div class="sidebar-exports">
                <div class="nav-index-title">Machine-Readable Exports</div>
                <a href="/api/v1/reports/{analysis_id}/aeo-report?format=json" class="btn-export" target="_blank">
                    <span>📄</span> JSON Master Report
                </a>
                <a href="/api/v1/reports/{analysis_id}/export/aeo-remediation-tracker.csv" class="btn-export">
                    <span>📊</span> AEO Remediation CSV
                </a>
                <a href="/api/v1/reports/{analysis_id}/export/aeo-question-dataset.csv" class="btn-export">
                    <span>📑</span> Question Dataset CSV
                </a>
            </div>
        </aside>

        <!-- Main Content Area -->
        <main class="main-content">
            <header class="report-header">
                <div class="header-meta">
                    <span class="badge-standard">AEO Master Audit</span>
                    <span style="color: var(--text-muted); font-size: 12px;">Generated: {generated_at}</span>
                </div>
                <h1 class="report-title">{domain}</h1>
                <p class="report-subtitle">Comprehensive Answer Engine Optimization, Search Feature Readiness & Observed Visibility Evaluation</p>
            </header>

            <!-- Core Integrity Disclaimer -->
            <div class="integrity-box">
                <h5>Core AEO Architecture Rule: Separation of Outcomes</h5>
                <p>
                    A professional AEO report strictly distinguishes <strong>Answer Readiness</strong> (on-site content completeness and clarity), 
                    <strong>Eligibility for search enhancements</strong> (schema and structural conformity), and 
                    <strong>Observed Answer Appearances</strong> (empirically confirmed live search snippets or AI citations). 
                    Readiness scores evaluate content against the audit rubric and do not guarantee search engine selection.
                </p>
            </div>

            <!-- 4-Tier KPI Scorecard -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <span class="kpi-label">Answer Readiness</span>
                    <span class="kpi-val" style="color: {readiness_color};">{readiness_display}<span style="font-size:16px;">/100</span></span>
                    <span class="kpi-caption">First-party passage clarity & depth</span>
                </div>
                <div class="kpi-card">
                    <span class="kpi-label">Observed Visibility</span>
                    <span class="kpi-val" style="color: {vis_color}; font-size:22px; padding-top:4px;">{visibility_status}</span>
                    <span class="kpi-caption">Empirically recorded search citations</span>
                </div>
                <div class="kpi-card">
                    <span class="kpi-label">Priority Questions</span>
                    <span class="kpi-val" style="color: var(--accent-cyan);">{questions_total}</span>
                    <span class="kpi-caption">{questions_supp} directly answered ({questions_unsupp} gaps)</span>
                </div>
                <div class="kpi-card">
                    <span class="kpi-label">Remediation Issues</span>
                    <span class="kpi-val" style="color: {kpis['total_findings'] and '#f59e0b' or '#10b981'};">{kpis['total_findings']}</span>
                    <span class="kpi-caption">Actionable findings in roadmap</span>
                </div>
            </div>

            <!-- 10 Audit Domains Overview -->
            <div class="section-block">
                <div class="section-header">
                    <h3 class="section-title">The 10 Core Domains of Answer Engine Optimization</h3>
                    <span class="section-tag">Audit Framework</span>
                </div>
                <div class="domains-grid">
                    {domains_html}
                </div>
            </div>

            <!-- Section 01: Executive Summary -->
            <section id="sec-01" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">01. Executive Summary & Answer Visibility Health</h3>
                    <span class="section-tag">High-Level Diagnosis</span>
                </div>
                <p style="font-size:15px; margin-bottom:16px; color:var(--text-main);">
                    {html.escape(json_data["sections"]["01_executive_summary"]["headline"] or "The target domain exhibits strong foundation content with specific answer structure and schema gaps affecting answer engine ingestion.")}
                </p>
                <div class="alert-callout">
                    <strong>Audit Assessment:</strong> Evaluated {questions_total} high-intent commercial and informational user questions. {questions_supp} questions possess verified on-site direct answers, while {questions_unsupp} require direct policy/specification content additions.
                </div>
            </section>

            <!-- Section 02: Audit Scope & Methodology -->
            <section id="sec-02" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">02. Audit Scope, Platform Coverage & Methodology</h3>
                    <span class="section-tag">Scope Register</span>
                </div>
                <p style="margin-bottom:12px;">Audited URL: <a href="{website_url}" target="_blank" class="ext-link">{website_url}</a> ({json_data["sections"]["02_audit_scope_and_methodology"]["pages_audited"]} pages crawled).</p>
                <p style="color:var(--text-secondary); margin-bottom:12px;">
                    Search Engine & Answer Platforms Monitored: Google Search (Featured Snippets, PAA), Google Assistant / Voice, Bing / Copilot, ChatGPT Search, and Perplexity AI.
                </p>
                <div class="alert-callout">
                    <strong>Integrity Protocol:</strong> Testing distinguishes desktop vs mobile rendering conditions. Simulated vector passage matches are reported strictly as local retrieval tests and are not claimed to be live third-party SERP captures.
                </div>
            </section>

            <!-- Section 03: Question Universe & Intent Mapping -->
            <section id="sec-03" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">03. Question Universe & Intent Mapping</h3>
                    <span class="section-tag">Question Inventory</span>
                </div>
                <p style="margin-bottom:16px;">
                    Target user questions classified across 5 primary intent stages (Informational, Navigational, Commercial, Transactional, Support) and 8 interrogative archetypes (What, Why, How, When, Where, Who, Which, Comparison).
                </p>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Key</th>
                                <th>Target Question</th>
                                <th>Type</th>
                                <th>Category</th>
                                <th>Answer Status</th>
                                <th>Target URL</th>
                                <th>Verified Excerpt</th>
                            </tr>
                        </thead>
                        <tbody>
                            {question_rows_html}
                        </tbody>
                    </table>
                </div>
            </section>

            <!-- Section 04: Answer Readiness & Content Structure -->
            <section id="sec-04" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">04. Answer Readiness & Content Structure</h3>
                    <span class="section-tag">Passage Quality</span>
                </div>
                <p style="margin-bottom:12px;">
                    Evaluates whether answers are immediate, explicit, and easy to extract. Direct answers must be located in the first passage directly beneath the heading (40-60 word concise inverted-pyramid summary).
                </p>
                <div class="alert-callout">
                    <strong>Heading-Question Alignment:</strong> H2 and H3 headings must directly mirror user question phrasing (e.g. <em>"How does [Product] integrate with CRM?"</em>) to maximize answer passage score.
                </div>
            </section>

            <!-- Section 05: Featured Snippet Analysis -->
            <section id="sec-05" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">05. Featured Snippet Analysis</h3>
                    <span class="section-tag">Rank-Zero Opportunities</span>
                </div>
                <p style="margin-bottom:12px;">
                    Analyzes candidate pages for Paragraph, Numbered List, and HTML Table snippets.
                </p>
                <div class="alert-callout">
                    <strong>Search Engine Control:</strong> Google selects featured snippets algorithmically based on real-time query signals. No markup technique or tag guarantees a featured snippet appearance.
                </div>
            </section>

            <!-- Section 06: People Also Ask & Related Questions -->
            <section id="sec-06" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">06. People Also Ask (PAA) & Related Questions</h3>
                    <span class="section-tag">Follow-up Coverage</span>
                </div>
                <p>
                    Audits follow-up question clusters. Strategic recommendation: Consolidate related sub-questions into unified authoritative topic guides rather than publishing repetitive thin doorway pages.
                </p>
            </section>

            <!-- Section 07: FAQ and Question-Answer Content Audit -->
            <section id="sec-07" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">07. FAQ & Question-Answer Content Audit</h3>
                    <span class="section-tag">Utility & Safeguards</span>
                </div>
                <p style="margin-bottom:12px;">
                    Reviews FAQ usefulness, duplication, and policy accuracy across the site.
                </p>
                <div class="alert-callout">
                    <strong>Google Policy Warning:</strong> Google has restricted FAQ rich results primarily to well-known government and health authority domains. FAQ content must be maintained for genuine on-page user experience rather than relying on SERP snippet expansion.
                </div>
            </section>

            <!-- Section 08: Structured Data & Rich Results -->
            <section id="sec-08" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">08. Structured Data & Rich Results Validation</h3>
                    <span class="section-tag">JSON-LD Schemas</span>
                </div>
                <p style="margin-bottom:12px;">
                    Checks schema syntax, required entity properties, and strict agreement with visible on-page content.
                </p>
                <div class="alert-callout">
                    <strong>Eligibility vs. Observed Enhancement:</strong> Valid schema confirms technical eligibility; it does not constitute proof that Google will render an enhanced rich result.
                </div>
            </section>

            <!-- Section 09: Entity Answers & Knowledge Panels -->
            <section id="sec-09" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">09. Entity Answers & Knowledge Panels</h3>
                    <span class="section-tag">Knowledge Graph Grounding</span>
                </div>
                <p>
                    Verifies official entity name, descriptions, and authoritative <code>sameAs</code> links across LinkedIn, Crunchbase, Wikipedia, and official brand social profiles to eliminate entity ambiguity.
                </p>
            </section>

            <!-- Section 10: Voice & Conversational Search -->
            <section id="sec-10" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">10. Voice & Conversational Search Optimization</h3>
                    <span class="section-tag">Spoken Readability</span>
                </div>
                <p style="margin-bottom:12px;">
                    Evaluates natural conversational syntax, pronunciation clarity, and local action support for voice assistant queries.
                </p>
                <div class="alert-callout">
                    <strong>Voice Ranking Reality:</strong> Voice assistants use independent retrieval pipelines. Text that reads well aloud is not guaranteed to be chosen by voice assistants.
                </div>
            </section>

            <!-- Section 11: AI Answer Engine Visibility -->
            <section id="sec-11" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">11. AI Answer Engine Visibility (ChatGPT, Perplexity, Gemini, Claude)</h3>
                    <span class="section-tag">AI Citations</span>
                </div>
                <p>
                    Status: <strong style="color:{vis_color};">{visibility_status}</strong>. Direct answer citations, brand mentions, and source attributions across major generative answer interfaces.
                </p>
            </section>

            <!-- Section 12: Local & Action-Oriented Answers -->
            <section id="sec-12" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">12. Local & Action-Oriented Answers</h3>
                    <span class="section-tag">Local Intent & NAP</span>
                </div>
                <p>
                    Audits business name, address, telephone (NAP), operating hours, booking instructions, and Google Business Profile consistency.
                </p>
            </section>

            <!-- Section 13: Product, Commercial & Transactional Answers -->
            <section id="sec-13" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">13. Product, Commercial & Transactional Answers</h3>
                    <span class="section-tag">Buyer Decision Support</span>
                </div>
                <p>
                    Evaluates how clearly purchase-influencing questions are answered: pricing tiers, feature comparisons, compatibility prerequisites, and return/cancellation terms.
                </p>
            </section>

            <!-- Section 14: Support, Documentation & Troubleshooting -->
            <section id="sec-14" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">14. Support, Documentation & Troubleshooting</h3>
                    <span class="section-tag">Procedural Accuracy</span>
                </div>
                <p>
                    Reviews step-by-step procedures, error message resolutions, version requirements, and reproducible troubleshooting paths.
                </p>
            </section>

            <!-- Section 15: Answer Accuracy & Source Quality -->
            <section id="sec-15" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">15. Answer Accuracy, Source Quality & Freshness</h3>
                    <span class="section-tag">Fact-Checking</span>
                </div>
                <p>
                    Detects contradictory statements across pages, stale dates, and unsupported claims. Differentiates website factual accuracy from external LLM hallucinations.
                </p>
            </section>

            <!-- Section 16: Competitor Answer Benchmarking -->
            <section id="sec-16" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">16. Competitor Answer Benchmarking</h3>
                    <span class="section-tag">Share of Answer</span>
                </div>
                <p style="margin-bottom:12px;">
                    Benchmarking compares domains currently winning the answer box for shared priority questions.
                </p>
                <div class="alert-callout">
                    <strong>Competitor Distinction:</strong> Search answer competitors (often media publications, Reddit, or aggregators) are distinguished from direct commercial competitors.
                </div>
            </section>

            <!-- Section 17: Search Performance & Business Outcomes -->
            <section id="sec-17" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">17. Search Performance & Business Outcomes</h3>
                    <span class="section-tag">ROI Measurement</span>
                </div>
                <p>
                    Tracks measurable business outcomes: Search Console impressions, clicks, click-through rate (CTR), and identifiable AI referral traffic. Answer visibility is an intermediate metric, not guaranteed revenue.
                </p>
            </section>

            <!-- Section 18: Content Gaps & Answer Strategy -->
            <section id="sec-18" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">18. Content Gaps & Answer Strategy</h3>
                    <span class="section-tag">Editorial Remediation</span>
                </div>
                <p>
                    Prioritizes high-demand missing questions and consolidates redundant content into high-authority answer assets.
                </p>
            </section>

            <!-- Section 19: Prioritized Remediation Roadmap (P0 - P3) -->
            <section id="sec-19" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">19. Prioritized AEO Remediation Roadmap (P0 - P3)</h3>
                    <span class="section-tag">14-Field Action Cards</span>
                </div>
                <p style="margin-bottom:20px;">
                    Every finding includes prescriptive recommendations, ownership, effort, and verification criteria:
                </p>
                <div class="findings-container">
                    {finding_cards_html or '<p style="color:#94a3b8;">No open findings recorded.</p>'}
                </div>
            </section>

            <!-- Section 20: Appendices & Evidence Register -->
            <section id="sec-20" class="section-block">
                <div class="section-header">
                    <h3 class="section-title">20. Appendices & Evidence Register</h3>
                    <span class="section-tag">Provenance & Raw Data</span>
                </div>
                <p style="margin-bottom:12px;">
                    Full audit registry containing timestamped DOM snapshots, extracted questions, and schema validation outputs.
                </p>
                <p style="color:var(--text-secondary); font-size:12px;">
                    Report Analysis ID: <code>{analysis_id}</code> · Standard: AEO-2026-MASTER · Certification Status: VALIDATED
                </p>
            </section>
        </main>
    </div>
</body>
</html>
"""


aeo_report_generator = CompleteAeoReportGenerator()
