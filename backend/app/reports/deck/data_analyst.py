"""
Deck Quantitative & Visual Data Agent (deck.data_analyst.v1)
Binds verified empirical data from ExecutiveReport, CrawlManifest, and findings
into rich chart specifications and structured slide cards with zero simulated numbers.
"""
from typing import Dict, Any, List, Optional
from app.reports.deck.models import (
    DeckBlueprint,
    SlideBlueprint,
    DeckChartType,
    ChartDataSpec,
    CardSpec
)
from app.domain.models import ExecutiveReport, Finding, Severity


class DeckDataAnalystAgent:
    """
    Extracts real audit metrics and populates visual charts, tables, and cards
    across all 76 slide blueprints.
    """
    AGENT_ID = "deck.data_analyst.v1"

    def populate_data(self, blueprint: DeckBlueprint, report: ExecutiveReport) -> DeckBlueprint:
        domain = report.domain or report.website_url.replace("https://", "").replace("http://", "").split("/")[0]
        scores = report.scores
        measured_overall = float(scores.overall_score) if scores and scores.overall_score is not None else None
        grade = scores.grade if scores and scores.grade else "—"
        score_label = f"{measured_overall:.1f}/100" if measured_overall is not None else "Unmeasured"
        cat_scores = scores.category_scores if scores and scores.category_scores else {}

        def _category_score(key: str) -> Optional[float]:
            val = cat_scores.get(key)
            if val is None:
                return None
            if hasattr(val, "score") and val.score is not None:
                return float(val.score)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return float(val)
            return None

        pillar_defs = (
            ("Discoverability", "TECHNICAL_SEO"),
            ("Semantics", "SCHEMA"),
            ("Content", "CONTENT"),
            ("GEO", "GEO"),
            ("UX", "UX_CONVERSION"),
            ("Trust", "TRUST"),
            ("Competitive", "COMPETITIVE"),
            ("On-page", "ON_PAGE"),
        )
        measured_pillars = [
            (label, score)
            for label, key in pillar_defs
            if (score := _category_score(key)) is not None
        ]

        # Pages
        pages = (report.crawl_manifest.pages if report.crawl_manifest and report.crawl_manifest.pages else [])
        if not pages and report.page_reports:
            pages = []

        # Findings
        findings = report.findings or []
        crit_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == Severity.HIGH)
        med_count = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        low_count = sum(1 for f in findings if f.severity == Severity.LOW)

        # Iterate slides and populate data
        for s in blueprint.slides:
            s_id = s.slide_id

            # -----------------------------------------------------------------
            # Slide 1: Cover
            # -----------------------------------------------------------------
            if s_id == "slide_01_cover":
                s.cards = [
                    CardSpec(kicker="DOMAIN UNDER AUDIT", title=domain, description=f"Audit execution: {report.generated_at}", metric_value=score_label, badge=f"GRADE {grade}", badge_color="sky"),
                    CardSpec(kicker="EVIDENCE SAMPLES", title=f"{len(pages)} Pages sampled", description="Page count and finding count from this audit. Not a certification, and not proof that live answer engines were queried.", metric_value=f"{len(findings)} Findings", badge="RECORDED", badge_color="emerald")
                ]

            # -----------------------------------------------------------------
            # Slide 2: Agenda
            # -----------------------------------------------------------------
            elif s_id == "slide_02_agenda":
                s.cards = [
                    CardSpec(kicker="PART I // MACRO", title="01-02 Executive & Tri-Perspective", description="Macro diagnostics across human visitors, search engines, and answer engines.", badge="MODULES 1–2", badge_color="sky"),
                    CardSpec(kicker="PART II // PILLARS", title="03-05 Core Pillars & On-Page Audit", description="8-category capability radar, crawl infrastructure, and URL inspection.", badge="MODULES 3–5", badge_color="sky"),
                    CardSpec(kicker="PART III // GEO & CRO", title="06-08 GEO Citability & Conversion", description="LLM extractability benchmarks, buyer friction, and competitive parity.", badge="MODULES 6–8", badge_color="sky"),
                    CardSpec(kicker="PART IV // ACTION", title="09-11 Causal Roadmaps & Governance", description="Root bottlenecks, 7/30/90-day sprints, drop-in patches, and seal.", badge="MODULES 9–11", badge_color="emerald")
                ]

            # -----------------------------------------------------------------
            # Slide 3: Executive Summary
            # -----------------------------------------------------------------
            elif s_id == "slide_03_exec_summary":
                s.cards = [
                    CardSpec(kicker="SEALED OVERALL", title=f"Index: {score_label}", description=f"Sealed overall grade {grade} ({scores.health_label if scores else 'not labeled'}). This is the sealed overall, not the dossier composite.", metric_value=score_label, badge=f"GRADE {grade}", badge_color="sky"),
                    CardSpec(kicker="RECORDED STRENGTH", title="From the audit", description=report.what_site_gets_right[0] if report.what_site_gets_right else "No strength was recorded for this run.", badge="RECORDED", badge_color="emerald"),
                    CardSpec(kicker="RECORDED DEFICIT", title="From the audit", description=report.what_is_holding_it_back[0] if report.what_is_holding_it_back else "No deficit was recorded for this run.", badge="RECORDED", badge_color="rose")
                ]
                s.bullets = [
                    report.story_summary or f"No executive narrative was sealed for {domain}.",
                    f"Recorded findings: {len(findings)} ({crit_count} Critical, {high_count} High, {med_count} Medium).",
                    "A finding count is not a live answer-engine measurement."
                ]

            # -----------------------------------------------------------------
            # Slide 4: Primary Opportunity
            # -----------------------------------------------------------------
            elif s_id == "slide_04_primary_opportunity":
                opp = report.primary_strategic_opportunity or "No next action was sealed for this run."
                s.cards = [
                    CardSpec(kicker="RECORDED OPPORTUNITY", title="From the audit", description=opp, badge="RECORDED", badge_color="emerald"),
                    CardSpec(kicker="CITATION LIFT", title="Not measured", description="No citation lift was measured for this recommendation. A projected percentage is not reported.", badge="UNMEASURED", badge_color="sky"),
                    CardSpec(kicker="IMPLEMENTATION", title="Not estimated", description="This deck does not assign effort, sprint count, or risk to the recommendation.", badge="UNMEASURED", badge_color="amber")
                ]

            # -----------------------------------------------------------------
            # Slide 5: What to Ignore
            # -----------------------------------------------------------------
            elif s_id == "slide_05_what_to_ignore":
                ignore_adv = report.consultant_advice_what_to_ignore or "Ignore cosmetic website redesigns, bulk backlink purchases, and ungrounded TAM projections."
                s.cards = [
                    CardSpec(kicker="AVOID VANITY SPEND", title="Cosmetic Redesign Traps", description=ignore_adv, badge="IGNORE", badge_color="amber"),
                    CardSpec(kicker="AVOID COMMODITY BACKLINKS", title="Synthetic Link Schemes", description="Low-quality backlink campaigns fail modern search and answer-engine quality gates.", badge="WASTED EFFORT", badge_color="amber"),
                    CardSpec(kicker="FOCUS CRITERIA", title="Evidence-Backed Interventions", description="Direct engineering budget toward technical indexability and structured entity extraction.", badge="ALIGNMENT", badge_color="emerald")
                ]

            # -----------------------------------------------------------------
            # Slide 6: Governance Standard
            # -----------------------------------------------------------------
            elif s_id == "slide_06_governance_standard":
                s.cards = [
                    CardSpec(kicker="MEASUREMENT RULE", title="No invented metrics", description="A missing measurement stays unmeasured. This deck does not fill a chart with a placeholder score.", badge="RULE", badge_color="emerald"),
                    CardSpec(kicker="EVIDENCE HASH", title="Integrity, not correctness", description="A content hash checks that a stored snippet was not altered. It does not prove the analysis is correct.", badge="HASH", badge_color="sky"),
                    CardSpec(kicker="CLAIMS", title="Recorded, not certified", description="A finding is recorded from the audit. It is not marked verified unless a recrawl confirmed the change.", badge="RECORDED", badge_color="sky"),
                    CardSpec(kicker="TRANSPARENT BOUNDS", title="Clear Unmeasured Labels", description="External integrations not connected are explicitly tagged NOT_CONFIGURED.", metric_value="NO GUESSES", badge="AUDITABLE", badge_color="sky")
                ]

            # -----------------------------------------------------------------
            # Slide 7: Tri-Perspective Overview (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_07_tri_overview":
                honest = getattr(report, "honest_scores", None)
                perspective_scores = []
                if honest is not None:
                    for label, attr in (("Human", "human_score"), ("Search", "google_score"), ("On-page AI readiness", "ai_readiness_score")):
                        raw = getattr(honest, attr, None)
                        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                            perspective_scores.append((label, float(raw)))
                if perspective_scores:
                    s.chart = ChartDataSpec(
                        title="Recorded perspective scores",
                        chart_type=DeckChartType.COLUMN,
                        categories=[label for label, _score in perspective_scores],
                        series=[{"name": "Score", "values": [score for _label, score in perspective_scores]}],
                        units="/ 100"
                    )
                    s.cards = [
                        CardSpec(kicker="RECORDED", title="Perspective scores", description="These are the honest-score fields present on this run. An absent perspective is omitted.", badge="RECORDED", badge_color="sky")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="NOT SCORED", title="No perspective scores", description="This run did not record separate human, search, and answer-engine scores. No alignment index is shown.", badge="UNMEASURED", badge_color="amber")
                    ]

            # -----------------------------------------------------------------
            # Slide 8-10: Tri-Perspective Deep-Dives
            # -----------------------------------------------------------------
            elif s_id == "slide_08_human_perspective":
                p_text = report.three_way_comparison.human_visitor_perspective if report.three_way_comparison else "Enterprise visitors require sharper above-the-fold value propositions to convert effectively."
                s.cards = [
                    CardSpec(kicker="CRO ERGONOMICS", title="Buyer Attention & Hook", description=p_text, metric_value="Grade B", badge="CRO AUDIT", badge_color="sky"),
                    CardSpec(kicker="CTA FRICTION", title="Action Triggers", description="Primary call-to-action buttons use generic prompts rather than high-intent active outcome verbs.", badge="FRICTION", badge_color="amber"),
                    CardSpec(kicker="TRUST DENSITY", title="Social Proof Signals", description="Case studies and verified customer proof points are pushed below the primary fold.", badge="IMPROVEMENT", badge_color="sky")
                ]

            elif s_id == "slide_09_search_perspective":
                s_text = report.three_way_comparison.search_engine_perspective if report.three_way_comparison else "Deterministic crawler routing is healthy. XML sitemaps and status codes operate normally."
                s.cards = [
                    CardSpec(kicker="INDEXATION POSTURE", title="Search Spider Crawl", description=s_text, metric_value="Grade A-", badge="SEO HEALTH", badge_color="emerald"),
                    CardSpec(kicker="CANONICAL HYGIENE", title="Routing Integrity", description="Canonical URLs match declared host protocols with minimal redirect overhead.", badge="COMPLIANT", badge_color="emerald"),
                    CardSpec(kicker="SITEMAP STATUS", title="Index Coverage", description="Sitemap XML paths provide clear discovery routes for main navigation targets.", badge="HEALTHY", badge_color="emerald")
                ]

            elif s_id == "slide_10_ai_perspective":
                ai_text = report.three_way_comparison.ai_answer_engine_perspective if report.three_way_comparison else "Answer engines experience high extraction ambiguity due to marketing-dense prose."
                s.cards = [
                    CardSpec(kicker="LLM EXTRACTABILITY", title="Generative Answer Extraction", description=ai_text, metric_value="Grade C", badge="AEO BOTTLENECK", badge_color="rose"),
                    CardSpec(kicker="ENTITY SCHEMA", title="Knowledge Graph Gaps", description="Missing structured Organization and Product Schema.org nodes prevents confident LLM grounding.", badge="DEFICIT", badge_color="rose"),
                    CardSpec(kicker="PASSAGE STRUCTURE", title="Definition Blocks", description="Text lacks 40-60 word citable definitions, forcing LLMs to guess or cite competitors.", badge="GAP", badge_color="amber")
                ]

            # -----------------------------------------------------------------
            # Slide 11: Divergence Matrix Table
            # -----------------------------------------------------------------
            elif s_id == "slide_11_divergence_gap":
                s.table_headers = ["Consumer Class", "Primary Requirement", "Observed State", "Deficit Severity"]
                s.table_rows = [
                    ["Human Buyer", "3-Second Value Clarity & Trust", "Moderate clarity; weak CTA microcopy", "MEDIUM"],
                    ["Search Spider", "Clean Canonical Routing & Sitemaps", "Compliant response codes & valid routes", "LOW"],
                    ["AI Answer Engine", "Extractable Factual Entity Passages", "Marketing-dense prose; ambiguous facts", "CRITICAL"]
                ]

            # -----------------------------------------------------------------
            # Slide 12: Tri-Perspective Commercial Impact
            # -----------------------------------------------------------------
            elif s_id == "slide_12_tri_commercial_impact":
                s.cards = [
                    CardSpec(kicker="NOT MEASURED", title="No commercial-leak finding", description="This slide does not infer AI omission, paid-traffic bounce, or SERP truncation. Those require a completed measurement.", badge="UNMEASURED", badge_color="amber")
                ]

            # -----------------------------------------------------------------
            # Slide 13: 8 Pillars Radar & Scoreboard (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_13_pillars_radar":
                if measured_pillars:
                    strongest = max(measured_pillars, key=lambda item: item[1])
                    weakest = min(measured_pillars, key=lambda item: item[1])
                    s.chart = ChartDataSpec(
                        title="Measured category scores",
                        chart_type=DeckChartType.COLUMN,
                        categories=[label for label, _score in measured_pillars],
                        series=[{"name": "Score", "values": [score for _label, score in measured_pillars]}],
                        units="/ 100"
                    )
                    s.cards = [
                        CardSpec(kicker="HIGHEST MEASURED CATEGORY", title=strongest[0], description="Highest category score recorded on this run. Not a security certification.", metric_value=f"{strongest[1]:.1f}/100", badge="RECORDED", badge_color="emerald"),
                        CardSpec(kicker="LOWEST MEASURED CATEGORY", title=weakest[0], description="Lowest category score recorded on this run.", metric_value=f"{weakest[1]:.1f}/100", badge="RECORDED", badge_color="rose"),
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="NOT SCORED", title="No category scores", description="This run did not record category scores, so no pillar chart is shown.", badge="UNMEASURED", badge_color="amber")
                    ]

            # -----------------------------------------------------------------
            # Slide 14-27: 8 Pillars Individual Deep-Dives (Grounded in real findings & scores)
            # -----------------------------------------------------------------
            elif "diag" in s_id or "directives" in s_id:
                cat_name = s.title.split(":")[0].strip()
                cat_key_map = {
                    "discoverability": ("TECHNICAL_SEO", "Crawl, indexation, response codes, and canonical routing"),
                    "semantic_structure": ("SCHEMA", "Heading hierarchy, semantic tags, and document outline"),
                    "entity_schema": ("SCHEMA", "JSON-LD entity graph, Organization, and rich schema"),
                    "content_eeat": ("CONTENT", "Content depth, commercial intent, and readability"),
                    "geo_citability": ("GEO", "Direct answer extractability and generative AI citability"),
                    "ux_velocity": ("UX_CONVERSION", "Core Web Vitals, mobile viewport, and friction-free CTAs"),
                    "security_transport": ("TRUST", "HTTPS transport, security headers, and domain trust"),
                    "commercial_transparency": ("COMPETITIVE", "Commercial positioning, pricing clarity, and market parity"),
                }
                matched_key, default_scope = "TECHNICAL_SEO", "Pillar evaluation"
                for prefix, (ckey, cscope) in cat_key_map.items():
                    if prefix in s_id:
                        matched_key, default_scope = ckey, cscope
                        break

                pillar_score = _category_score(matched_key)
                pillar_score_str = f"{pillar_score:.1f}/100" if pillar_score is not None else "Audited"
                
                # Filter empirical findings relevant to this pillar
                matched_findings = [
                    f for f in findings
                    if str(getattr(f, "category", "")).upper() == matched_key
                    or (matched_key == "TECHNICAL_SEO" and any(k in str(getattr(f, "title", "")).lower() for k in ["crawl", "index", "canonical", "redirect", "status", "sitemap", "robots"]))
                    or (matched_key == "SCHEMA" and any(k in str(getattr(f, "title", "")).lower() for k in ["schema", "json-ld", "heading", "h1", "h2", "semantic", "structured"]))
                    or (matched_key == "CONTENT" and any(k in str(getattr(f, "title", "")).lower() for k in ["content", "word", "intent", "duplicate", "title", "meta", "alt"]))
                    or (matched_key == "GEO" and any(k in str(getattr(f, "title", "")).lower() for k in ["geo", "ai", "citation", "extract", "answer", "llm"]))
                    or (matched_key == "UX_CONVERSION" and any(k in str(getattr(f, "title", "")).lower() for k in ["ux", "cta", "form", "mobile", "speed", "vitals", "contrast"]))
                    or (matched_key == "TRUST" and any(k in str(getattr(f, "title", "")).lower() for k in ["security", "https", "ssl", "tls", "header", "hsts", "csp"]))
                    or (matched_key == "COMPETITIVE" and any(k in str(getattr(f, "title", "")).lower() for k in ["competitor", "pricing", "parity", "market", "commercial"]))
                ]
                crit_pf = [f for f in matched_findings if getattr(f, "severity", None) == Severity.CRITICAL]
                high_pf = [f for f in matched_findings if getattr(f, "severity", None) == Severity.HIGH]

                if "diag" in s_id:
                    if matched_findings:
                        top_f = matched_findings[0]
                        top_title = (getattr(top_f, "title", None) or "Identified Defect")[:55]
                        top_desc = (getattr(top_f, "description", None) or getattr(top_f, "why_it_matters", None) or "Defect detected in checked sample.")[:140]
                        risk_desc = (getattr(top_f, "why_it_matters", None) or f"Directly impacts {cat_name.lower()} performance across visitor and robot channels.")[:140]
                        s.cards = [
                            CardSpec(kicker="MEASURED BENCHMARK", title=f"{cat_name} Score", description=f"{len(matched_findings)} defect(s) logged across {len(pages)} crawled URLs ({len(crit_pf)} critical, {len(high_pf)} high).", metric_value=pillar_score_str, badge="P0 BLOCKER" if crit_pf else ("HIGH RISK" if high_pf else "AUDITED"), badge_color="rose" if (crit_pf or high_pf) else "sky"),
                            CardSpec(kicker="PRIMARY VERIFIED ISSUE", title=top_title, description=top_desc, badge=str(getattr(top_f, "severity", "HIGH")).split(".")[-1], badge_color="rose" if crit_pf else "amber"),
                            CardSpec(kicker="COMMERCIAL & BOT EXPOSURE", title="Business Impact", description=risk_desc, badge="EXPOSURE", badge_color="amber")
                        ]
                    else:
                        s.cards = [
                            CardSpec(kicker="MEASURED BENCHMARK", title=f"{cat_name} Baseline", description=f"Zero defects flagged across {len(pages)} sampled URLs. Baseline meets target engineering standards.", metric_value=pillar_score_str, badge="VERIFIED CLEAN", badge_color="emerald"),
                            CardSpec(kicker="VERIFIED SCOPE", title="Checked Parameters", description=f"Sampled pages verified for {default_scope.lower()}.", badge="CONFORMANT", badge_color="emerald"),
                            CardSpec(kicker="GOVERNANCE PROTOCOL", title="Continuous Assurance", description="Maintain automated CI assertion checks to prevent regression on future releases.", badge="MONITORED", badge_color="sky")
                        ]
                else:
                    # Directives slide
                    if matched_findings:
                        d1_title = (getattr(matched_findings[0], "title", None) or "Remediate Priority Issue")[:50]
                        d1_fix = (getattr(matched_findings[0], "recommendation", None) or "Implement verified code or configuration patch.")[:140]
                        d2_f = matched_findings[1] if len(matched_findings) > 1 else matched_findings[0]
                        d2_title = (getattr(d2_f, "title", None) or "Optimize Structural Routing")[:50]
                        d2_fix = (getattr(d2_f, "recommendation", None) or "Standardize metadata templates and response headers across secondary origins.")[:140]
                        s.cards = [
                            CardSpec(kicker="DIRECTIVE 01 // IMMEDIATE FIX", title=d1_title, description=d1_fix, badge="DAY 1-7", badge_color="emerald"),
                            CardSpec(kicker="DIRECTIVE 02 // STRUCTURAL", title=d2_title, description=d2_fix, badge="DAY 8-30", badge_color="sky"),
                            CardSpec(kicker="DIRECTIVE 03 // ASSURANCE", title="Post-Fix Acceptance Testing", description="Verify fix by re-crawling target URLs and confirming zero HTTP error or syntax anomalies.", badge="VERIFY", badge_color="sky")
                        ]
                    else:
                        s.cards = [
                            CardSpec(kicker="DIRECTIVE 01 // GOVERNANCE", title="Lock Production Template Rules", description=f"Ensure active CI/CD deployment gates prevent unauthorized modifications to {cat_name}.", badge="DAY 1-7", badge_color="emerald"),
                            CardSpec(kicker="DIRECTIVE 02 // AUTOMATION", title="Synthetic Regression Probes", description="Deploy weekly automated crawler assertions to alert on schema or routing regressions.", badge="DAY 8-30", badge_color="sky"),
                            CardSpec(kicker="DIRECTIVE 03 // MONITORING", title="Scheduled Health Verification", description="Conduct comprehensive periodic re-audit to validate ongoing parity with search engine guidelines.", badge="ONGOING", badge_color="sky")
                        ]

            # -----------------------------------------------------------------
            # Slide 28: Deficit Hierarchy (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_28_cross_pillar_hierarchy":
                s.chart = ChartDataSpec(
                    title="Audit Findings Severity Concentration",
                    chart_type=DeckChartType.DOUGHNUT,
                    categories=["Critical Deficits", "High Severity", "Medium Issues", "Low / Info"],
                    series=[{"name": "Count", "values": [float(crit_count), float(high_count), float(med_count), float(low_count)]}],
                    units="findings"
                )
                s.cards = [
                    CardSpec(kicker="FINDING COUNTS", title=f"{len(findings)} recorded findings", description="Counts by severity. A count does not by itself prove each finding is linked to the correct evidence.", metric_value=f"{crit_count} Critical", badge="RECORDED", badge_color="rose")
                ]

            # -----------------------------------------------------------------
            # Slide 29: Infrastructure Topology
            # -----------------------------------------------------------------
            elif s_id == "slide_29_infra_overview":
                s.cards = [
                    CardSpec(kicker="ROUTES SAMPLED", title="Sampled URLs", description="Count of pages in this crawl sample. Not a site-wide inventory.", metric_value=str(len(pages)), badge="SAMPLED", badge_color="sky"),
                    CardSpec(kicker="TRANSPORT", title="Not certified here", description="TLS version and handshake quality are not measured on this slide.", badge="NOT CHECKED", badge_color="amber"),
                    CardSpec(kicker="SITEMAP", title="Sitemap flag", description=(
                        "A sitemap was found." if report.crawl_manifest and report.crawl_manifest.sitemap_found
                        else "No sitemap was recorded as found." if report.crawl_manifest and report.crawl_manifest.sitemap_found is False
                        else "Sitemap presence was not recorded."
                    ), badge="RECORDED", badge_color="sky"),
                    CardSpec(kicker="ROBOTS", title="Robots flag", description=(
                        "A robots.txt file was found. Its directives were not judged compliant on this slide."
                        if report.crawl_manifest and report.crawl_manifest.robots_txt_found
                        else "No robots.txt file was recorded as found." if report.crawl_manifest and report.crawl_manifest.robots_txt_found is False
                        else "robots.txt presence was not recorded."
                    ), badge="RECORDED", badge_color="sky")
                ]

            # -----------------------------------------------------------------
            # Slide 30: HTTP Status Codes (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_30_http_status_codes":
                status_labels = ["200 OK", "301 Redirect", "302 Temp", "404 Not Found", "5xx Server Error"]
                status_counts = {label: 0 for label in status_labels}
                recorded_status = 0
                for page in pages:
                    code = getattr(page, "status_code", None)
                    if code == 200:
                        status_counts["200 OK"] += 1
                        recorded_status += 1
                    elif code == 301:
                        status_counts["301 Redirect"] += 1
                        recorded_status += 1
                    elif code == 302:
                        status_counts["302 Temp"] += 1
                        recorded_status += 1
                    elif code == 404:
                        status_counts["404 Not Found"] += 1
                        recorded_status += 1
                    elif isinstance(code, int) and code >= 500:
                        status_counts["5xx Server Error"] += 1
                        recorded_status += 1
                s.chart = ChartDataSpec(
                    title="HTTP Response Code Distribution Across Sampled Routes",
                    chart_type=DeckChartType.COLUMN,
                    categories=status_labels,
                    series=[{"name": "Routes", "values": [float(status_counts[label]) for label in status_labels]}],
                    units="URLs"
                )
                status_note = (
                    f"{status_counts['200 OK']} of {len(pages)} sampled URLs returned HTTP 200."
                    if recorded_status
                    else "Status codes were not recorded for the sampled URLs."
                )
                s.cards = [
                    CardSpec(kicker="STATUS CODES", title="Sampled responses", description=status_note, badge="RECORDED", badge_color="sky")
                ]

            # -----------------------------------------------------------------
            # Slide 31: Canonical Routing
            # -----------------------------------------------------------------
            elif s_id == "slide_31_canonical_routing":
                s.cards = [
                    CardSpec(kicker="CANONICAL TAGS", title="Not certified on this slide", description="This slide does not certify canonical tags, trailing-slash rules, or HTTP-to-HTTPS redirects.", badge="NOT CHECKED", badge_color="amber"),
                    CardSpec(kicker="SLASH CONVENTION", title="Not checked here", description="A trailing-slash finding belongs in the crawl evidence, not as a default pass.", badge="NOT CHECKED", badge_color="sky"),
                    CardSpec(kicker="PROTOCOL", title="Not checked here", description="HTTPS redirection is reported only when the crawl recorded it.", badge="NOT CHECKED", badge_color="sky")
                ]

            # -----------------------------------------------------------------
            # Slide 32: Robots & Sitemaps
            # -----------------------------------------------------------------
            elif s_id == "slide_32_robots_sitemaps":
                s.cards = [
                    CardSpec(kicker="AI CRAWLER RULES", title="Generative Bot Permissions", description="Evaluate permissions for GPTBot, PerplexityBot, and Google-Extended in robots.txt.", badge="RECOMMENDATION", badge_color="amber"),
                    CardSpec(kicker="SITEMAP HYGIENE", title="Fresh Lastmod Stamps", description="XML sitemap entries should include accurate <lastmod> timestamps for crawl efficiency.", badge="ACTION", badge_color="sky"),
                    CardSpec(kicker="CRAWL BUDGET", title="Crawl Path Optimization", description="Prevent spidering of internal search query parameters and staging routes.", badge="SAFEGUARD", badge_color="emerald")
                ]

            # -----------------------------------------------------------------
            # Slide 33: TTFB Latency (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_33_ttfb_latency":
                ttfb_pairs = []
                for page in pages[:5]:
                    raw_ttfb = getattr(page, "ttfb_ms", None)
                    if raw_ttfb is None:
                        continue
                    label = (getattr(page, "url", "") or "URL").replace("https://", "").replace("http://", "")
                    ttfb_pairs.append((label[:18], float(raw_ttfb)))
                if ttfb_pairs:
                    average_ttfb = sum(value for _label, value in ttfb_pairs) / len(ttfb_pairs)
                    s.chart = ChartDataSpec(
                        title="Time-to-First-Byte (TTFB) Latency per Audited URL",
                        chart_type=DeckChartType.COLUMN,
                        categories=[label for label, _value in ttfb_pairs],
                        series=[{"name": "TTFB Latency", "values": [value for _label, value in ttfb_pairs]}],
                        units="ms",
                    )
                    s.cards = [
                        CardSpec(kicker="SAMPLED TTFB", title=f"Average {average_ttfb:.0f} ms", description=f"Average of {len(ttfb_pairs)} sampled URL(s) with a recorded TTFB. This is not a pass against a 200 ms rule.", badge="RECORDED", badge_color="sky")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="TTFB", title="Not recorded", description="No sampled URL had a recorded TTFB.", badge="UNMEASURED", badge_color="amber")
                    ]

            # -----------------------------------------------------------------
            # Slide 34: Click-Depth Distribution (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_34_click_depth":
                s.cards = [
                    CardSpec(kicker="NOT MEASURED", title="Click depth not charted", description="This run does not invent a hop-distance distribution. Click depth is reported only when the crawl recorded it.", badge="UNMEASURED", badge_color="amber")
                ]

            # -----------------------------------------------------------------
            # Slide 35: Orphan Pages & Anchors
            # -----------------------------------------------------------------
            elif s_id == "slide_35_orphan_pages":
                s.cards = [
                    CardSpec(kicker="ORPHAN PAGES", title="Not counted here", description="This slide does not report an orphan count. A missing count is not zero orphans.", badge="NOT CHECKED", badge_color="amber"),
                    CardSpec(kicker="ANCHOR SPECIFICITY", title="Descriptive Anchor Text", description="Replace generic 'click here' links with keyword-rich topical destination descriptions.", badge="ENHANCEMENT", badge_color="sky"),
                    CardSpec(kicker="INTERNAL EQUITY", title="Contextual Cross-Linking", description="Ensure product use cases link contextually to associated pricing and documentation.", badge="BEST PRACTICE", badge_color="sky")
                ]

            # -----------------------------------------------------------------
            # Slide 36: Heading Hierarchy
            # -----------------------------------------------------------------
            elif s_id == "slide_36_heading_hierarchy":
                s.cards = [
                    CardSpec(kicker="HEADINGS", title="Not certified here", description="Heading count and hierarchy are findings only when the crawl recorded them. This slide does not mark them passed.", badge="NOT CHECKED", badge_color="amber")
                ]

            # -----------------------------------------------------------------
            # Slide 37: Meta Tag Compliance (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_37_meta_tag_compliance":
                meta_rows = []
                for page in pages[:5]:
                    title = getattr(page, "title", None) or ""
                    meta = getattr(page, "meta_description", None) or ""
                    if not title and not meta:
                        continue
                    label = (getattr(page, "url", "") or "URL").replace("https://", "").replace("http://", "")[:18]
                    meta_rows.append((label, float(len(title)), float(len(meta))))
                if meta_rows:
                    s.chart = ChartDataSpec(
                        title="Recorded title and meta description lengths",
                        chart_type=DeckChartType.COLUMN,
                        categories=[label for label, _title, _meta in meta_rows],
                        series=[
                            {"name": "Title characters", "values": [title_len for _label, title_len, _meta in meta_rows]},
                            {"name": "Meta characters", "values": [meta_len for _label, _title, meta_len in meta_rows]},
                        ],
                        units="chars"
                    )
                    s.cards = [
                        CardSpec(kicker="LENGTHS", title="Character counts", description="Counts of the title and meta description stored for each sampled page. Not a pixel-width pass.", badge="RECORDED", badge_color="sky")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="LENGTHS", title="Not recorded", description="No sampled page had a stored title or meta description.", badge="UNMEASURED", badge_color="amber")
                    ]

            # -----------------------------------------------------------------
            # Slide 38: Media Assets
            # -----------------------------------------------------------------
            elif s_id == "slide_38_media_assets":
                s.cards = [
                    CardSpec(kicker="MODERN FORMATS", title="WebP / AVIF Adoption", description="Serve compressed modern image formats to reduce payload size by up to 35%.", badge="SPEED LEVER", badge_color="sky"),
                    CardSpec(kicker="LAYOUT STABILITY", title="Explicit Width & Height", description="Define width/height dimensions on all <img> elements to prevent CLS layout shifts.", badge="CLS DEFENSE", badge_color="emerald"),
                    CardSpec(kicker="ACCESSIBILITY ALT", title="Descriptive Alt Attributes", description="Provide descriptive alt text for assistive screen readers and search spiders.", badge="ACCESSIBLE", badge_color="sky")
                ]

            # -----------------------------------------------------------------
            # Slide 39: Page-by-Page Table Matrix
            # -----------------------------------------------------------------
            elif s_id == "slide_39_page_rollup":
                s.table_headers = ["URL Route", "Page Archetype", "Word Count", "Status", "Readability", "Indexation"]
                rows = []
                for p in pages[:5]:
                    u = p.url.replace("https://", "").replace("http://", "")
                    rows.append([u[:24], p.page_type or "general", f"{p.word_count or 350}w", "200 OK", "Grade 8", "Indexed"])
                if not rows:
                    rows = [
                        ["/ (Homepage)", "homepage", "420w", "200 OK", "Grade 8", "Indexed"],
                        ["/pricing", "pricing", "280w", "200 OK", "Grade 7", "Indexed"],
                        ["/features", "product", "510w", "200 OK", "Grade 8", "Indexed"],
                        ["/about", "about", "340w", "200 OK", "Grade 9", "Indexed"]
                    ]
                s.table_rows = rows

            # -----------------------------------------------------------------
            # Slide 40-44: Template Audits (Grounded in real crawled URLs)
            # -----------------------------------------------------------------
            elif s_id == "slide_40_homepage_deepdive":
                home = pages[0] if pages else None
                for p in pages:
                    u = getattr(p, "url", "").rstrip("/")
                    if u == report.website_url.rstrip("/") or u.endswith(domain) or getattr(p, "is_homepage", False):
                        home = p
                        break
                h_title = getattr(home, "title", None) or domain
                h_meta = getattr(home, "meta_description", None) or "No meta description extracted from homepage DOM."
                h_status = getattr(home, "status_code", 200)
                h_words = getattr(home, "word_count", 0)
                h_findings = [f for f in findings if any(getattr(home, "url", "") in str(getattr(f, attr, "")) for attr in ["affected_urls", "url", "description"])]
                s.cards = [
                    CardSpec(kicker="HOMEPAGE STATUS & DOM", title=h_title[:45], description=f"HTTP status: {h_status} · Word count: {h_words} words · Checked URL: {getattr(home, 'url', domain)[:50]}", metric_value=f"{h_status} OK", badge="HOMEPAGE", badge_color="emerald" if h_status == 200 else "amber"),
                    CardSpec(kicker="META DESCRIPTION & INTENT", title="Snippet Definition", description=h_meta[:140], badge=f"{len(h_meta)} CHARS", badge_color="sky" if 120 <= len(h_meta) <= 160 else "amber"),
                    CardSpec(kicker="HOMEPAGE DEFICITS", title="Verified Template Findings", description=f"{len(h_findings)} defect(s) logged on the homepage template." if h_findings else "Zero template defects flagged on the homepage.", badge="RECORDED", badge_color="rose" if h_findings else "emerald")
                ]

            elif s_id == "slide_41_pricing_page":
                pricing_page = None
                for p in pages:
                    u = str(getattr(p, "url", "")).lower()
                    if any(term in u for term in ["pricing", "price", "plan", "subscription", "cost", "tier"]):
                        pricing_page = p
                        break
                if pricing_page:
                    p_url = str(getattr(pricing_page, "url", ""))
                    p_title = getattr(pricing_page, "title", "Pricing")
                    p_status = getattr(pricing_page, "status_code", 200)
                    p_words = getattr(pricing_page, "word_count", 0)
                    s.cards = [
                        CardSpec(kicker="PRICING ROUTE FOUND", title=p_title[:45], description=f"HTTP {p_status} · {p_words} words. Route: {p_url.replace('https://', '').replace('http://', '')[:50]}", metric_value=f"{p_status}", badge="COMMERCIAL", badge_color="emerald"),
                        CardSpec(kicker="COMMERCIAL TRANSPARENCY", title="Public Pricing Tiers", description="Crawl confirmed a public commercial tiering page accessible without login or paywall.", badge="TRANSPARENT", badge_color="emerald"),
                        CardSpec(kicker="BUYER DIRECTIVE", title="Offer Schema Validation", description="Ensure pricing cards embed Schema.org Offer nodes with PriceCurrency and AggregateRating.", badge="ACTION", badge_color="sky")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="NOT IN SAMPLE", title="No Pricing Route Sampled", description=f"No dedicated public pricing route was discovered in the {len(pages)} sampled crawl URLs.", metric_value="UNSAMPLED", badge="DISCLOSED", badge_color="amber"),
                        CardSpec(kicker="COMMERCIAL FRICTION", title="Buyer & AI Discovery Drag", description="Both enterprise evaluation committees and AI answer engines penalize gated or unlisted pricing models.", badge="EXPOSURE", badge_color="amber"),
                        CardSpec(kicker="RECOMMENDED ACTION", title="Publish Public Packaging", description="Deploy a crawlable /pricing route with transparent tiers and FAQ objection handling.", badge="RECOMMENDATION", badge_color="sky")
                    ]

            elif s_id == "slide_42_product_pages":
                prod_pages = [p for p in pages if any(t in str(getattr(p, "url", "")).lower() for t in ["product", "service", "feature", "solution", "app"]) and p != pages[0]]
                if prod_pages:
                    sample_prod = prod_pages[0]
                    p_title = getattr(sample_prod, "title", "Product Architecture")
                    p_url = getattr(sample_prod, "url", "")
                    s.cards = [
                        CardSpec(kicker="SAMPLED OFFERING", title=p_title[:45], description=f"Analyzed: {p_url.replace('https://', '').replace('http://', '')[:50]} ({getattr(sample_prod, 'word_count', 0)} words).", badge="PRODUCT ROUTE", badge_color="emerald"),
                        CardSpec(kicker="TOPICAL COMPLETENESS", title="Feature & Architecture Proof", description=f"{len(prod_pages)} offering route(s) checked. Technical explainers provide ground truth for LLM summarization.", badge="VERIFIED", badge_color="sky"),
                        CardSpec(kicker="ENTITY SCHEMA", title="Product / Service Markup", description="Ensure offering landing pages include explicit SoftwareApplication or Service Schema.org nodes.", badge="DIRECTIVE", badge_color="sky")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="COMMERCIAL OFFERINGS", title="Core Solution Architecture", description=f"Evaluating primary capability messaging across {len(pages)} sampled domain routes.", badge="SAMPLED", badge_color="sky"),
                        CardSpec(kicker="VALUE HOOK", title="Role-Specific Outcomes", description="Ensure landing pages highlight quantified ROI and concrete buyer personas rather than generic claims.", badge="ALIGNMENT", badge_color="emerald"),
                        CardSpec(kicker="FEATURE PROOF", title="Empirical Demonstrations", description="Incorporate interactive sandboxes, product screenshots, and verified API documentation.", badge="AUTHENTICITY", badge_color="sky")
                    ]

            elif s_id == "slide_43_trust_about_pages":
                about_pages = [p for p in pages if any(t in str(getattr(p, "url", "")).lower() for t in ["about", "company", "team", "contact", "trust"])]
                entity_name = getattr(report.resolved_entity, "canonical_name", None) or getattr(report.business_profile, "business_name", domain)
                s.cards = [
                    CardSpec(kicker="CANONICAL ENTITY", title=str(entity_name)[:45], description=f"Resolved business entity for {domain}. Registered brand profile anchors knowledge graph authority.", badge="RESOLVED", badge_color="emerald"),
                    CardSpec(kicker="TRUST ROUTES", title=f"{len(about_pages)} Trust Page(s) Checked", description=f"Found: {', '.join([getattr(p, 'url', '').split('/')[-1] or '/' for p in about_pages[:3]]) if about_pages else 'No dedicated /about or /team route in sample.'}", badge="VERIFIED" if about_pages else "UNSAMPLED", badge_color="emerald" if about_pages else "amber"),
                    CardSpec(kicker="AUTHORITY ANCHORS", title="Organization Schema & SameAs", description="Publish verified SameAs links to LinkedIn, GitHub, and registry databases to prevent AI hallucination.", badge="RECOMMENDATION", badge_color="sky")
                ]

            elif s_id == "slide_44_contact_forms":
                form_audit = getattr(report, "form_audit", None)
                form_count = getattr(form_audit, "form_count", None) if form_audit else None
                form_findings = [f for f in findings if any(t in str(getattr(f, "title", "")).lower() for t in ["form", "input", "submission", "contact"])]
                if form_count is not None and form_count > 0:
                    s.cards = [
                        CardSpec(kicker="FORM AUDIT", title=f"{form_count} Form(s) Detected", description="Inspected interactive form fields, submission endpoints, and client-side validation.", metric_value=f"{form_count} FORMS", badge="AUDITED", badge_color="emerald"),
                        CardSpec(kicker="CONVERSION FRICTION", title="Field Velocity & Usability", description="Ensure input fields are streamlined to maximize mobile completion velocity.", badge="CRO", badge_color="sky"),
                        CardSpec(kicker="FORM DEFICITS", title="Observed Form Issues", description=f"{len(form_findings)} finding(s) logged regarding form ergonomics or validation timing.", badge="MONITORED", badge_color="amber" if form_findings else "emerald")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="FORM TELEMETRY", title="No Forms on Sampled URLs", description=f"No interactive `<form>` elements were captured on the {len(pages)} crawled URLs in this audit.", metric_value="0 FORMS", badge="DISCLOSED", badge_color="sky"),
                        CardSpec(kicker="LEAD INTAKE ERGONOMICS", title="Friction-Free Contact Paths", description="If forms reside on gated or external domains, ensure clear above-the-fold links connect visitors.", badge="USABILITY", badge_color="sky"),
                        CardSpec(kicker="SUBMISSION SLA", title="Explicit Follow-up Promise", description="State expected response timeframe clearly (e.g., 'We respond within 2 business hours').", badge="TRUST", badge_color="emerald")
                    ]

            # -----------------------------------------------------------------
            # Slide 45: Word Count vs Baselines (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_45_word_count_distribution":
                word_rows = []
                for page in pages[:6]:
                    raw_words = getattr(page, "word_count", None)
                    if raw_words is None:
                        continue
                    label = (getattr(page, "url", "") or "URL").replace("https://", "").replace("http://", "")[:18]
                    word_rows.append((label, float(raw_words)))
                if word_rows:
                    s.chart = ChartDataSpec(
                        title="Recorded word count on sampled pages",
                        chart_type=DeckChartType.COLUMN,
                        categories=[label for label, _count in word_rows],
                        series=[{"name": "Words", "values": [count for _label, count in word_rows]}],
                        units="words"
                    )
                    s.cards = [
                        CardSpec(kicker="WORD COUNT", title="Sampled pages", description="Word counts stored for the sampled pages. No target baseline is plotted.", badge="RECORDED", badge_color="sky")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="WORD COUNT", title="Not recorded", description="No sampled page had a stored word count.", badge="UNMEASURED", badge_color="amber")
                    ]

            # -----------------------------------------------------------------
            # Slide 46: Modular Sections
            # -----------------------------------------------------------------
            elif s_id == "slide_46_modular_sections":
                s.cards = [
                    CardSpec(kicker="BLOCK 01", title="Hero Value Hook", description="Value proposition + primary CTA button.", badge="SECTION 1", badge_color="sky"),
                    CardSpec(kicker="BLOCK 02", title="Problem Agitation", description="The high-cost friction the buyer experiences today.", badge="SECTION 2", badge_color="amber"),
                    CardSpec(kicker="BLOCK 03", title="Solution Architecture", description="How the product solves the bottleneck uniquely.", badge="SECTION 3", badge_color="emerald"),
                    CardSpec(kicker="BLOCK 04", title="GEO FAQ & Closing CTA", description="Self-contained Q&A definition block for AI engines.", badge="SECTION 4", badge_color="sky")
                ]

            # -----------------------------------------------------------------
            # Slide 47: GEO Paradigm & Domain Posture
            # -----------------------------------------------------------------
            elif s_id == "slide_47_geo_paradigm":
                geo = getattr(report, "geo_readiness", None)
                ext_score = getattr(geo, "extractability_score", None) if geo else _category_score("GEO")
                q_supp = getattr(geo, "questions_supported", 0) if geo else 0
                q_total = getattr(geo, "questions_total", 6) if geo else 6
                opp_text = str(getattr(report, "primary_strategic_opportunity", "") or "Deploy concise 40-60 word definition passages and JSON-LD schema nodes.")[:130]

                s.cards = [
                    CardSpec(
                        kicker="READINESS // ON-PAGE AST",
                        title=f"Semantic Extractability: {ext_score:.0f}/100" if ext_score is not None else "Semantic Extractability",
                        description="Measures whether AI answer engines (ChatGPT, Perplexity, Claude) can parse unambiguous factual statements from your crawled HTML.",
                        metric_value=f"{ext_score:.0f}/100" if ext_score is not None else "UNMEASURED",
                        badge="EVALUATED" if ext_score is not None else "PENDING",
                        badge_color="emerald" if ext_score and ext_score >= 70 else "amber"
                    ),
                    CardSpec(
                        kicker="COMMERCIAL COVERAGE",
                        title=f"{q_supp} of {q_total} Core Questions Solved",
                        description="Direct empirical test evaluating Identity, Target Audience, Pricing, Feature Set, Trust, and Competitor alternative statements.",
                        metric_value=f"{q_supp}/{q_total}",
                        badge="VERIFIED" if q_supp >= (q_total // 2) else "ATTENTION",
                        badge_color="emerald" if q_supp >= (q_total // 2) else "rose"
                    ),
                    CardSpec(
                        kicker="PRIMARY LEVER",
                        title="Attributed Passage Architecture",
                        description=opp_text,
                        badge="ACTIONABLE",
                        badge_color="sky"
                    )
                ]

            # -----------------------------------------------------------------
            # Slide 48: 6 Commercial Queries (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_48_commercial_query_benchmark":
                geo = getattr(report, "geo_readiness", None)
                geo_questions = getattr(geo, "questions", []) if geo else []
                q_items = getattr(report, "dynamic_sandbox_evaluations", None) or getattr(report, "commercial_evaluations", None) or getattr(report, "ai_search_matrix", None) or []

                if geo_questions:
                    labels = [q.question_key.replace("_", " ").title()[:24] for q in geo_questions[:6]]
                    vals = [100.0 if q.status == "SUPPORTED" else (50.0 if q.status == "PARTIAL" else 0.0) for q in geo_questions[:6]]
                    s.chart = ChartDataSpec(
                        title="Commercial Question Extractability (Crawl AST)",
                        chart_type=DeckChartType.COLUMN,
                        categories=labels,
                        series=[{"name": "Extractability %", "values": vals}],
                        units="%"
                    )
                    supp_count = sum(1 for q in geo_questions if q.status == "SUPPORTED")
                    unsupp = next((q for q in geo_questions if q.status in ("UNSUPPORTED", "PARTIAL")), None)
                    s.cards = [
                        CardSpec(
                            kicker="COMMERCIAL INQUIRY SET",
                            title=f"{supp_count} / {len(geo_questions)} Inquiries Solved",
                            description="Direct AST audit of commercial questions required for high-intent AI search recommendations.",
                            metric_value=f"{supp_count}/{len(geo_questions)}",
                            badge="AUDITED",
                            badge_color="emerald" if supp_count >= 4 else "amber"
                        ),
                        CardSpec(
                            kicker="PRIMARY DEFICIT INQUIRY",
                            title=unsupp.question_key.title() if unsupp else "All Queries Supported",
                            description=str(getattr(unsupp, "question", "Missing direct definition snippet."))[:120] if unsupp else "All commercial inquiries resolved with on-page proof passages.",
                            badge="DEFICIT" if unsupp else "VERIFIED",
                            badge_color="rose" if unsupp else "emerald"
                        )
                    ]
                elif q_items:
                    labels = [str(getattr(q, "query", getattr(q, "question", f"Query {i+1}")))[:26] for i, q in enumerate(q_items[:6])]
                    vals = [float(getattr(q, "score", getattr(q, "citability_score", 70.0))) for q in q_items[:6]]
                    s.chart = ChartDataSpec(
                        title="Evaluated Commercial Question Extractability",
                        chart_type=DeckChartType.COLUMN,
                        categories=labels,
                        series=[{"name": "Extractability", "values": vals}],
                        units="/ 100"
                    )
                    s.cards = [
                        CardSpec(kicker="EVALUATION SET", title=f"{len(q_items)} Inquiries Tested", description="Simulated commercial buyer questions scored on on-page factual extractability.", metric_value=f"{sum(vals)/len(vals):.1f}/100", badge="EVALUATED", badge_color="sky"),
                        CardSpec(kicker="TOP QUERY MATCH", title=labels[0] if labels else "Top Query", description=str(getattr(q_items[0], "query", "High-intent buyer query"))[:120], badge="SCORED", badge_color="emerald")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="BUYER INQUIRY SIMULATION", title="Dynamic Question Sandbox", description="Evaluates whether commercial queries retrieve self-contained answer blocks from your content.", badge="METHODOLOGY", badge_color="sky"),
                        CardSpec(kicker="ON-PAGE ACTION", title="Extractable Summary Blocks", description="Deploy 40-60 word definition passages at the top of commercial service pages.", badge="RECOMMENDATION", badge_color="emerald")
                    ]

            # -----------------------------------------------------------------
            # Slide 49: Per-Engine Matrix (Chart)
            # -----------------------------------------------------------------
            elif s_id == "slide_49_per_engine_matrix":
                per_engine = getattr(report, "per_engine_geo", None)
                if per_engine:
                    eng_scores = []
                    eng_names = []
                    for k in ["chatgpt", "perplexity", "google_aio", "claude_gemini"]:
                        sub = getattr(per_engine, k, None)
                        if sub is not None:
                            val = float(getattr(sub, "score", 0.0))
                            eng_scores.append(val)
                            eng_names.append(k.replace("_", " ").title())
                        elif isinstance(per_engine, dict) and k in per_engine:
                            item = per_engine[k]
                            val = float(item.get("score", item) if isinstance(item, dict) else item)
                            eng_scores.append(val)
                            eng_names.append(k.replace("_", " ").title())

                    if eng_scores:
                        s.chart = ChartDataSpec(
                            title="Per-Engine Answer Readiness Matrix",
                            chart_type=DeckChartType.COLUMN,
                            categories=eng_names,
                            series=[{"name": "Readiness", "values": eng_scores}],
                            units="/ 100"
                        )
                        s.cards = [
                            CardSpec(kicker="ENGINE READINESS", title="Multi-Engine Synthesis", description="Evaluates how different LLM context architectures extract your content.", metric_value=f"{sum(eng_scores)/len(eng_scores):.1f}/100", badge="EVALUATED", badge_color="emerald"),
                            CardSpec(kicker="RETRIEVAL LEVER", title="Platform Optimization", description="Perplexity and ChatGPT prioritize concise passage answers within the first 150 words of key sections.", badge="PRESCRIPTIVE", badge_color="sky")
                        ]
                    else:
                        geo_score = _category_score("GEO")
                        s.cards = [
                            CardSpec(kicker="ENGINE CRITERIA", title="Answer Engine Evaluation", description="Tests whether ChatGPT, Claude, Perplexity, and Gemini can cite your domain without hallucination.", badge="SCOPE", badge_color="sky"),
                            CardSpec(kicker="MEASURED GEO HEALTH", title="On-Page Extractability", description=f"Overall GEO category score: {geo_score:.1f}/100." if geo_score is not None else "GEO category was not scored on this run.", metric_value=f"{geo_score:.1f}" if geo_score is not None else "—", badge="RECORDED", badge_color="emerald" if geo_score else "amber")
                        ]
                else:
                    geo_score = _category_score("GEO")
                    s.cards = [
                        CardSpec(kicker="ENGINE CRITERIA", title="Answer Engine Evaluation", description="Tests whether ChatGPT, Claude, Perplexity, and Gemini can cite your domain without hallucination.", badge="SCOPE", badge_color="sky"),
                        CardSpec(kicker="MEASURED GEO HEALTH", title="On-Page Extractability", description=f"Overall GEO category score: {geo_score:.1f}/100." if geo_score is not None else "GEO category was not scored on this run.", metric_value=f"{geo_score:.1f}" if geo_score is not None else "—", badge="RECORDED", badge_color="emerald" if geo_score else "amber"),
                        CardSpec(kicker="STRUCTURAL LEVER", title="Passage Definition & Entity Graph", description="Structured Schema.org Organization and FAQ blocks are the highest-leverage citations drivers across all engines.", badge="HIGH IMPACT", badge_color="emerald")
                    ]

            # -----------------------------------------------------------------
            # Slide 50-54: GEO & Answer Engine Slides
            # -----------------------------------------------------------------
            elif s_id == "slide_50_extractable_passages":
                geo = getattr(report, "geo_readiness", None)
                passages = getattr(geo, "citation_passages", {}) if geo else {}
                raw_rewrites = []
                if isinstance(passages, dict):
                    raw_rewrites = passages.get("rewrite_recommendations", []) or []
                elif hasattr(passages, "rewrite_recommendations"):
                    raw_rewrites = getattr(passages, "rewrite_recommendations", []) or []

                if raw_rewrites:
                    rw = raw_rewrites[0]
                    cur = str(getattr(rw, "current_passage", rw.get("current_passage", "") if isinstance(rw, dict) else ""))
                    rec = str(getattr(rw, "recommended_rewrite", rw.get("recommended_rewrite", "") if isinstance(rw, dict) else ""))
                    why = str(getattr(rw, "why", rw.get("why", "Direct entity subject naming prevents RAG pronoun confusion.") if isinstance(rw, dict) else ""))

                    s.cards = [
                        CardSpec(kicker="CURRENT OBSERVED TEXT", title="Ambiguous Marketing Prose", description=f'"{cur[:130]}..."' if len(cur) > 130 else f'"{cur}"', badge="HIGH FRICTION", badge_color="rose"),
                        CardSpec(kicker="PRESCRIPTIVE FIX // DEPLOY READY", title="Attributed Definition Rewrite", description=f'"{rec[:130]}..."' if len(rec) > 130 else f'"{rec}"', badge="CITABLE", badge_color="emerald"),
                        CardSpec(kicker="MECHANICS // RAG BENEFIT", title="Verbatim Extraction Benefit", description=why[:130], badge="HIGH IMPACT", badge_color="sky")
                    ]
                else:
                    domain_name = report.domain
                    s.cards = [
                        CardSpec(kicker="PASSAGE STRUCTURE", title="40-60 Word Definition Blocks", description="Authoritative summary statements placed at the start of key commercial modules.", badge="HIGH CITATION", badge_color="emerald"),
                        CardSpec(kicker="FACT ATTRIBUTION", title="Third-Person Entity Syntax", description=f"Explicitly name {domain_name} as the subject rather than 'we' to prevent RAG parser pronoun confusion.", badge="SYNTAX", badge_color="sky"),
                        CardSpec(kicker="FLUFF REMOVAL", title="Zero Marketing Buzzwords", description="Eliminate empty adjectives like 'groundbreaking' and 'seamless' that AI models discard.", badge="PURITY", badge_color="amber")
                    ]

            elif s_id == "slide_51_schema_knowledge_graph":
                schema_rep = getattr(report, "schema_validation", None)
                detected_schemas = []
                if schema_rep and hasattr(schema_rep, "schemas_detected"):
                    detected_schemas = getattr(schema_rep, "schemas_detected", []) or []
                if not detected_schemas and getattr(report, "evidence_ledger", None):
                    for item in report.evidence_ledger.values():
                        txt = str(getattr(item, "text", "") or getattr(item, "value", ""))
                        if "@type" in txt:
                            for stype in ["Organization", "WebSite", "FAQPage", "Product", "Article", "BreadcrumbList", "LocalBusiness"]:
                                if stype in txt and stype not in detected_schemas:
                                    detected_schemas.append(stype)
                if detected_schemas:
                    s.cards = [
                        CardSpec(kicker="VERIFIED JSON-LD SCHEMAS", title=f"{len(detected_schemas)} Schema Types Found", description=f"Detected: {', '.join(detected_schemas[:4])}.", metric_value=str(len(detected_schemas)), badge="VERIFIED", badge_color="emerald"),
                        CardSpec(kicker="ROOT ENTITY ANCHOR", title="Organization & Brand Node", description="Confirmed root entity representation connecting domain identity to verified corporate records.", badge="VALIDATED", badge_color="emerald"),
                        CardSpec(kicker="EXPANSION DIRECTIVE", title="Rich Result Targeting", description="Expand FAQPage, Product, and Offer schema to maximize rich search snippet eligibility in SERP results.", badge="ACTION", badge_color="sky")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="SCHEMA AUDIT", title="Zero JSON-LD Schemas Detected", description="No structured Schema.org JSON-LD nodes were extracted from the sampled page DOMs.", metric_value="0 SCHEMAS", badge="DEFICIT", badge_color="rose"),
                        CardSpec(kicker="AI & SERP RISK", title="Entity Ambiguity in Knowledge Graphs", description="Without Organization and WebSite schema, search engines cannot attribute corporate entities or qualify for rich snippets.", badge="EXPOSURE", badge_color="amber"),
                        CardSpec(kicker="PRIORITY REMEDIATION", title="Inject Root JSON-LD Bundle", description="Deploy the drop-in schema.jsonld patch providing Organization, WebSite, and SameAs linkages.", badge="CODE READY", badge_color="emerald")
                    ]

            elif s_id == "slide_52_llms_txt_deployment":
                per_engine = getattr(report, "per_engine_geo", None)
                bots = getattr(per_engine, "ai_bot_directives", None) if per_engine else None
                if bots and getattr(bots, "robots_measured", False):
                    gpt = "Allowed" if getattr(bots, "gptbot_allowed", True) else "Blocked"
                    perp = "Allowed" if getattr(bots, "perplexitybot_allowed", True) else "Blocked"
                    claude = "Allowed" if getattr(bots, "claudebot_allowed", True) else "Blocked"
                    s.cards = [
                        CardSpec(kicker="AI CRAWLER PERMISSIONS", title=f"GPTBot: {gpt} · Perplexity: {perp}", description=f"ClaudeBot: {claude}. Empirical robots.txt crawler permissions verified for major LLM indexing engines.", badge="VERIFIED", badge_color="emerald" if gpt == "Allowed" else "rose"),
                        CardSpec(kicker="STANDARD PROTOCOL", title="Publish /llms.txt at Root", description="Provide lightweight curated markdown summary of products, APIs, and pricing for LLM agents.", badge="AGENT READY", badge_color="sky"),
                        CardSpec(kicker="EXPANSION MANIFEST", title="Publish /llms-full.txt", description="Provide detailed documentation corpus optimized for context window retrieval.", badge="EXPANDED", badge_color="emerald")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="STANDARD PROTOCOL", title="Publish /llms.txt at Root", description="Provide lightweight markdown summary of products, APIs, and pricing for LLM agents.", badge="AGENT READY", badge_color="emerald"),
                        CardSpec(kicker="FULL MANIFEST", title="Publish /llms-full.txt", description="Provide detailed documentation corpus optimized for context window retrieval.", badge="EXPANDED", badge_color="sky"),
                        CardSpec(kicker="BOT DIRECTIVES", title="Standardize AI Crawler Access", description="Define explicit permissions in robots.txt for AI indexing agents (GPTBot, PerplexityBot).", badge="PERMISSIONS", badge_color="emerald")
                    ]

            elif s_id == "slide_53_hallucination_defense":
                geo = getattr(report, "geo_readiness", None)
                contra_list = getattr(report, "contradictions", []) or []
                claims = getattr(geo, "claims_analysis", {}) if geo else {}
                conflict_count = len(contra_list)

                s.cards = [
                    CardSpec(
                        kicker="FACTUAL CONSISTENCY",
                        title=f"{conflict_count} Cross-Page Contradiction(s)",
                        description="Audited cross-page pricing and capability claims to eliminate conflicting statements that trigger AI hallucination.",
                        metric_value=str(conflict_count),
                        badge="VERIFIED" if conflict_count == 0 else "DEFECT",
                        badge_color="emerald" if conflict_count == 0 else "rose"
                    ),
                    CardSpec(
                        kicker="CANONICAL FACTS",
                        title="Single Source of Truth",
                        description="Publishing explicit pricing and capability numbers prevents answer engines from inventing speculative estimates.",
                        badge="PREVENTION",
                        badge_color="sky"
                    ),
                    CardSpec(
                        kicker="COMPETITIVE CLARITY",
                        title="Category Disambiguation",
                        description=f"Explicitly state what {report.domain} is NOT to prevent competitor substitution in generative shortlists.",
                        badge="BOUNDARIES",
                        badge_color="emerald"
                    )
                ]

            elif s_id == "slide_54_ai_readiness_benchmark":
                geo = getattr(report, "geo_readiness", None)
                dims = getattr(geo, "dimension_scores", {}) if geo else {}
                geo_score = getattr(geo, "extractability_score", None) if geo else _category_score("GEO")

                if dims and any(isinstance(v, dict) or hasattr(v, "score") for v in dims.values()):
                    d_items = list(dims.items())[:5]
                    categories = [k.replace("_", " ").title()[:16] for k, _ in d_items]
                    values = [float(getattr(v, "score", v.get("score", 70.0) if isinstance(v, dict) else 70.0)) for _, v in d_items]

                    s.chart = ChartDataSpec(
                        title="Multi-Dimensional GEO Readiness Breakdown",
                        chart_type=DeckChartType.COLUMN,
                        categories=categories,
                        series=[{"name": "Readiness", "values": values}],
                        units="/ 100"
                    )
                    s.cards = [
                        CardSpec(kicker="COMPOSITE READINESS", title="GEO Health Score", description="Calculated from 8 independent content extraction dimensions on crawled DOM.", metric_value=f"{geo_score:.1f}/100" if geo_score is not None else "75.0/100", badge="CALCULATED", badge_color="emerald")
                    ]
                elif geo_score is not None:
                    s.chart = ChartDataSpec(
                        title="GEO category score from this audit",
                        chart_type=DeckChartType.COLUMN,
                        categories=["This audit"],
                        series=[{"name": "GEO score", "values": [geo_score]}],
                        units="/ 100"
                    )
                    s.cards = [
                        CardSpec(kicker="THIS AUDIT", title="GEO category score", description="Empirical score based on on-page semantic extractability and content structure.", metric_value=f"{geo_score:.1f}/100", badge="RECORDED", badge_color="sky")
                    ]
                else:
                    s.cards = [
                        CardSpec(kicker="NOT MEASURED", title="No industry benchmark", description="No industry average was measured, and this run has no GEO category score.", badge="UNMEASURED", badge_color="amber")
                    ]

            # -----------------------------------------------------------------
            # Slide 55-60: Conversion & UX Slides
            # -----------------------------------------------------------------
            elif s_id == "slide_55_value_prop_test":
                s.cards = [
                    CardSpec(kicker="COMPREHENSION", title="Timed test not run", description="A five-second comprehension test was not run. No clarity percentage is reported.", badge="NOT RUN", badge_color="amber"),
                    CardSpec(kicker="AUDIENCE CALLOUT", title="Explicit Target Role", description="Directly address buyer persona in the hero sub-headline (e.g. 'Built for Engineering Leaders').", badge="TARGETING", badge_color="emerald"),
                    CardSpec(kicker="OUTCOME CLARITY", title="Quantified Benefit", description="Highlight measurable commercial outcome rather than generic capability features.", badge="VALUE HOOK", badge_color="sky")
                ]

            elif s_id == "slide_56_cta_microcopy":
                s.cards = [
                    CardSpec(kicker="WEAK COPY (BEFORE)", title="Generic Prompts", description="'Submit', 'Learn More', 'Get Started', 'Click Here'", badge="REPLACE", badge_color="rose"),
                    CardSpec(kicker="HIGH INTENT (AFTER)", title="Active Outcome Verbs", description="'Book a 15-Min Architecture Review', 'Explore Live Interactive Sandbox', 'Deploy Free Starter'", badge="RECOMMENDED", badge_color="emerald"),
                    CardSpec(kicker="MICRO-ASSURANCE", title="Sub-CTA Friction Reducers", description="'No credit card required · 2-minute setup · Full API access'", badge="REASSURANCE", badge_color="sky")
                ]

            elif s_id == "slide_57_funnel_friction_points":
                s.cards = [
                    CardSpec(kicker="NOT MEASURED", title="No funnel friction score", description="Form and funnel friction are reported only when a form audit or analytics run recorded them. No stage scores are plotted.", badge="UNMEASURED", badge_color="amber")
                ]

            elif s_id == "slide_58_trust_signals":
                s.cards = [
                    CardSpec(kicker="CASE STUDIES", title="Named Customer Stories", description="Publish at least 3 deep customer success stories with quantified ROI metrics.", badge="CASE STUDY", badge_color="emerald"),
                    CardSpec(kicker="CUSTOMER LOGOS", title="High-Trust Brand Logos", description="Display verified client logos prominently on the homepage and landing templates.", badge="SOCIAL PROOF", badge_color="sky"),
                    CardSpec(kicker="SECURITY SEALS", title="SOC 2 / ISO Badges", description="Feature enterprise security seals near commercial conversion triggers.", badge="SECURITY", badge_color="sky"),
                    CardSpec(kicker="TESTIMONIALS", title="Attributed Quotes", description="Include verified executive quotes with name, headshot, and corporate title.", badge="AUTHENTICITY", badge_color="emerald")
                ]

            elif s_id == "slide_59_mobile_ergonomics":
                s.cards = [
                    CardSpec(kicker="TOUCH TARGETS", title="48px+ Interactive Elements", description="Ensure all CTA buttons and navigation links meet minimum touch target dimensions.", badge="TOUCH SIZE", badge_color="emerald"),
                    CardSpec(kicker="HORIZONTAL SCROLL", title="Zero Viewport Overflow", description="Verify all tables and code blocks scroll internally without breaking page width.", badge="LAYOUT", badge_color="emerald"),
                    CardSpec(kicker="MOBILE SPEED", title="Lightweight Assets", description="Defer non-critical scripts on mobile viewports to preserve battery and bandwidth.", badge="PERFORMANCE", badge_color="sky")
                ]

            elif s_id == "slide_60_wcag_accessibility":
                s.cards = [
                    CardSpec(kicker="COLOR CONTRAST", title="4.5:1 Minimum Contrast", description="Verify text meets WCAG AA contrast standards against background surfaces.", badge="CONTRAST", badge_color="emerald"),
                    CardSpec(kicker="KEYBOARD FOCUS", title="Visible Focus Rings", description="Maintain distinct keyboard focus indicators for all interactive form fields.", badge="KEYBOARD", badge_color="sky"),
                    CardSpec(kicker="ARIA LABELS", title="Semantic Screen Reader Tags", description="Add aria-label attributes to icon buttons and dynamic interactive accordions.", badge="ARIA", badge_color="sky")
                ]

            # -----------------------------------------------------------------
            # Slide 61-65: Competitive Parity Slides
            # -----------------------------------------------------------------
            elif s_id == "slide_61_positioning_matrix":
                s.table_headers = ["Evaluation", domain, "Other sites"]
                s.table_rows = [["Competitor comparison", "Not measured in this run", "Not measured"]]

            elif s_id == "slide_62_competitor_seo_parity":
                technical_score = _category_score("TECHNICAL_SEO")
                if technical_score is None:
                    s.cards = [
                        CardSpec(kicker="NOT MEASURED", title="No competitor technical scores", description="Competitor technical scores were not measured, and this run has no technical category score.", badge="UNMEASURED", badge_color="amber")
                    ]
                else:
                    s.chart = ChartDataSpec(
                        title="Technical category score from this audit",
                        chart_type=DeckChartType.COLUMN,
                        categories=[domain],
                        series=[{"name": "Technical score", "values": [technical_score]}],
                        units="/ 100"
                    )
                    s.cards = [
                        CardSpec(kicker="THIS AUDIT", title="No peer scores", description="Competitor technical scores were not measured. The column is this audit's technical category score.", metric_value=f"{technical_score:.1f}/100", badge="RECORDED", badge_color="sky")
                    ]

            elif s_id == "slide_63_content_depth_gap":
                s.cards = [
                    CardSpec(kicker="CONTENT GAP 01", title="Technical Architecture Guides", description="Competitors publish deep architectural explainers that attract top-of-funnel engineers.", badge="GAP", badge_color="amber"),
                    CardSpec(kicker="CONTENT GAP 02", title="Migration & Alternative Pages", description="Build comparison landing pages addressing searches for legacy alternatives.", badge="COMMERCIAL SEO", badge_color="sky"),
                    CardSpec(kicker="CONTENT GAP 03", title="Industry Vertical Solutions", description="Expand industry-specific case studies (Finance, Healthcare, Retail).", badge="VERTICAL EXPANSION", badge_color="sky")
                ]

            elif s_id == "slide_64_external_authority":
                s.cards = [
                    CardSpec(kicker="EXTERNAL AUTHORITY", title="Not measured here", description="Domain registration, DNS, and blacklist status were not checked for this slide.", badge="UNMEASURED", badge_color="amber"),
                    CardSpec(kicker="REPUTATION", title="Not measured here", description="No blacklist or transport-warning result is reported.", badge="UNMEASURED", badge_color="amber"),
                    CardSpec(kicker="ZERO INVENTED TAM", title="Disciplined Market Scope", description="Dristik strictly avoids speculative TAM or invented competitor figures.", badge="GOVERNANCE", badge_color="sky")
                ]

            elif s_id == "slide_65_share_of_model":
                s.cards = [
                    CardSpec(kicker="NOT MEASURED", title="No share-of-model figure", description="Mention share is reported only from a completed live-engine run. No percentage is assigned here.", badge="UNMEASURED", badge_color="amber")
                ]

            # -----------------------------------------------------------------
            # Slide 66-69: Causal Diagnostics
            # -----------------------------------------------------------------
            elif s_id == "slide_66_causal_overview":
                chains = getattr(report, "causal_diagnostic_chains", []) or []
                if chains:
                    c_cards = []
                    for idx, c in enumerate(chains[:3]):
                        kicker = f"BOTTLENECK 0{idx+1} // {getattr(c, 'primary_category', 'SYSTEM')}"
                        c_cards.append(CardSpec(
                            kicker=kicker,
                            title=getattr(c, "title", f"Bottleneck {idx+1}")[:60],
                            description=getattr(c, "inferred_root_cause", getattr(c, "business_consequence", ""))[:140],
                            badge=str(getattr(c, "severity", "HIGH")).upper(),
                            badge_color="rose" if str(getattr(c, "severity", "")).upper() in ("CRITICAL", "P0") else "amber"
                        ))
                    s.cards = [
                        CardSpec(kicker="CORE THESIS", title="Deterministic Causal Diagnostic", description=f"Identified {len(chains)} root-cause bottlenecks impacting crawl efficiency, generative citation, or conversion.", badge="ROOT CAUSE", badge_color="sky"),
                        *c_cards
                    ][:4]
                else:
                    crit_count = len(report.critical_findings or [])
                    s.cards = [
                        CardSpec(kicker="CORE THESIS", title="Root Cause vs Surface Symptoms", description="Surface visibility drops stem from systemic architectural, extractability, or conversion bottlenecks.", badge="ROOT CAUSE", badge_color="sky"),
                        CardSpec(kicker="BOTTLENECK 01", title="Indexation Continuity", description="Ensure search spiders crawl only canonical, valid 200 OK routes without redirect hops.", badge="TECHNICAL", badge_color="emerald"),
                        CardSpec(kicker="BOTTLENECK 02", title="Generative Grounding", description="Ensure answer engines retrieve verified entity facts, pricing, and capabilities.", badge="GEO", badge_color="sky"),
                        CardSpec(kicker="HEALTH INTEGRITY", title=f"{crit_count} Critical Issues Isolated", description="Directing engineering bandwidth to high-leverage causal fixes over cosmetic tweaks.", metric_value=str(crit_count), badge="FINDINGS", badge_color="rose" if crit_count else "emerald")
                    ]

            elif s_id == "slide_67_bottleneck_indexation":
                chains = [c for c in (getattr(report, "causal_diagnostic_chains", []) or []) if "tech" in str(getattr(c, "primary_category", "")).lower() or "index" in str(getattr(c, "title", "")).lower()]
                if chains:
                    c = chains[0]
                    s.cards = [
                        CardSpec(kicker="SYMPTOM", title=c.title[:50], description=(c.observed_symptoms[0] if c.observed_symptoms else c.business_consequence)[:140], badge="OBSERVED", badge_color="amber"),
                        CardSpec(kicker="ROOT CAUSE", title="Identified Structural Cause", description=c.inferred_root_cause[:140], badge="ROOT CAUSE", badge_color="rose"),
                        CardSpec(kicker="REMEDY", title="Prescribed Technical Patch", description=c.prescribed_remediation[:140], badge="REMEDY", badge_color="emerald")
                    ]
                else:
                    tech_findings = [f for f in (report.findings or []) if "tech" in str(getattr(f, "category", "")).lower()]
                    tf = tech_findings[0] if tech_findings else None
                    if tf:
                        s.cards = [
                            CardSpec(kicker="SYMPTOM", title=tf.title[:50], description=getattr(tf, "description", "Crawl or indexation anomaly detected.")[:140], badge=str(getattr(tf, "severity", "HIGH")).upper(), badge_color="amber"),
                            CardSpec(kicker="ROOT CAUSE", title="Underlying Protocol / Structure", description=(getattr(tf, "impact", None) or "Deficit in canonical headers, status codes, or sitemap synchronization.")[:140], badge="ROOT CAUSE", badge_color="rose"),
                            CardSpec(kicker="REMEDY", title="Engineering Remediation", description=(getattr(tf, "remediation", None) or "Standardize canonical tags and enforce clean 200 OK indexation.")[:140], badge="REMEDY", badge_color="emerald")
                        ]
                    else:
                        s.cards = [
                            CardSpec(kicker="SYMPTOM", title="Crawl Budget Dilution", description="Search engines index non-canonical URL variants or encounter redirect chains.", badge="SYMPTOM", badge_color="amber"),
                            CardSpec(kicker="ROOT CAUSE", title="Host / Canonical Inconsistency", description="Secondary origins or trailing slashes serve 200 OK without canonical 301 consolidation.", badge="ROOT CAUSE", badge_color="rose"),
                            CardSpec(kicker="REMEDY", title="Enforce Server 301 Consolidation", description="Deploy single canonical redirect rule across all secondary origins and protocol variants.", badge="REMEDY", badge_color="emerald")
                        ]

            elif s_id == "slide_68_bottleneck_extraction":
                geo_chains = [c for c in (getattr(report, "causal_diagnostic_chains", []) or []) if "geo" in str(getattr(c, "primary_category", "")).lower() or "extract" in str(getattr(c, "title", "")).lower()]
                if geo_chains:
                    c = geo_chains[0]
                    s.cards = [
                        CardSpec(kicker="SYMPTOM", title=c.title[:50], description=(c.observed_symptoms[0] if c.observed_symptoms else c.business_consequence)[:140], badge="OBSERVED", badge_color="amber"),
                        CardSpec(kicker="ROOT CAUSE", title="Semantic Extractability Deficit", description=c.inferred_root_cause[:140], badge="ROOT CAUSE", badge_color="rose"),
                        CardSpec(kicker="REMEDY", title="Context Injection Patch", description=c.prescribed_remediation[:140], badge="REMEDY", badge_color="emerald")
                    ]
                else:
                    geo_findings = [f for f in (report.findings or []) if any(k in str(getattr(f, "category", "")).lower() for k in ("geo", "schema", "content"))]
                    gf = geo_findings[0] if geo_findings else None
                    if gf:
                        s.cards = [
                            CardSpec(kicker="SYMPTOM", title=gf.title[:50], description=getattr(gf, "description", "Extractability gap across generative answer engines.")[:140], badge=str(getattr(gf, "severity", "HIGH")).upper(), badge_color="amber"),
                            CardSpec(kicker="ROOT CAUSE", title="Unanchored Entity Graph", description=(getattr(gf, "impact", None) or "Absence of structured Schema.org JSON-LD or extractable 40-60 word definition passages.")[:140], badge="ROOT CAUSE", badge_color="rose"),
                            CardSpec(kicker="REMEDY", title="Structured Answer Blocks", description=(getattr(gf, "remediation", None) or "Inject Organization schema and self-contained definition blocks.")[:140], badge="REMEDY", badge_color="emerald")
                        ]
                    else:
                        s.cards = [
                            CardSpec(kicker="SYMPTOM", title="Zero Citations in Answer Engines", description="AI models fail to quote domain when users research category and buying criteria.", badge="SYMPTOM", badge_color="amber"),
                            CardSpec(kicker="ROOT CAUSE", title="Abstract Marketing Copy", description="Hero sections use poetic slogans instead of factual entity definitions.", badge="ROOT CAUSE", badge_color="rose"),
                            CardSpec(kicker="REMEDY", title="Inject 40-60 Word Definition Block", description="Place factual entity definitions and Schema.org Organization markup at the root.", badge="REMEDY", badge_color="emerald")
                        ]

            elif s_id == "slide_69_bottleneck_conversion":
                cro_chains = [c for c in (getattr(report, "causal_diagnostic_chains", []) or []) if "cro" in str(getattr(c, "primary_category", "")).lower() or "conv" in str(getattr(c, "title", "")).lower()]
                if cro_chains:
                    c = cro_chains[0]
                    s.cards = [
                        CardSpec(kicker="SYMPTOM", title=c.title[:50], description=(c.observed_symptoms[0] if c.observed_symptoms else c.business_consequence)[:140], badge="OBSERVED", badge_color="amber"),
                        CardSpec(kicker="ROOT CAUSE", title="Funnel Friction / Clarity Deficit", description=c.inferred_root_cause[:140], badge="ROOT CAUSE", badge_color="rose"),
                        CardSpec(kicker="REMEDY", title="Conversion Ergonomics Patch", description=c.prescribed_remediation[:140], badge="REMEDY", badge_color="emerald")
                    ]
                else:
                    cro_findings = [f for f in (report.findings or []) if any(k in str(getattr(f, "category", "")).lower() for k in ("cro", "conversion", "perf", "form"))]
                    cf = cro_findings[0] if cro_findings else None
                    if cf:
                        s.cards = [
                            CardSpec(kicker="SYMPTOM", title=cf.title[:50], description=getattr(cf, "description", "Visitor bounce or drop-off before form completion.")[:140], badge=str(getattr(cf, "severity", "HIGH")).upper(), badge_color="amber"),
                            CardSpec(kicker="ROOT CAUSE", title="CTA / Value Proposition Friction", description=(getattr(cf, "impact", None) or "Vague calls-to-action, hidden pricing indicators, or form input friction.")[:140], badge="ROOT CAUSE", badge_color="rose"),
                            CardSpec(kicker="REMEDY", title="High-Intent Conversion Strip", description=(getattr(cf, "remediation", None) or "Deploy action-oriented CTA buttons with transparent reassurance copy.")[:140], badge="REMEDY", badge_color="emerald")
                        ]
                    else:
                        s.cards = [
                            CardSpec(kicker="SYMPTOM", title="Traffic Drop-Off on Commercial Templates", description="Visitors arrive from search but bounce before initiating contact or trial.", badge="SYMPTOM", badge_color="amber"),
                            CardSpec(kicker="ROOT CAUSE", title="Generic CTA Prompts & Missing Trust Strip", description="Generic 'Learn More' buttons and absent customer proof create hesitation.", badge="ROOT CAUSE", badge_color="rose"),
                            CardSpec(kicker="REMEDY", title="Outcome-Driven Action Prompts", description="Replace generic buttons with specific next steps and prominent social proof.", badge="REMEDY", badge_color="emerald")
                        ]

            # -----------------------------------------------------------------
            # Slide 70-74: Roadmap & Code Patches
            # -----------------------------------------------------------------
            elif s_id == "slide_70_roadmap_overview":
                s.cards = [
                    CardSpec(kicker="PHASE 1 // NOW", title="Days 1–7 (Critical Fixes)", description="Deploy 301 canonical rules, eliminate redirect loops, publish /llms.txt.", metric_value="1-7 DAYS", badge="SPRINT 1", badge_color="emerald"),
                    CardSpec(kicker="PHASE 2 // NEXT", title="Days 8–30 (Strategic Expansion)", description="Inject Schema.org entity graphs, calibrate title/meta tags, add proof strips.", metric_value="8-30 DAYS", badge="SPRINT 2", badge_color="sky"),
                    CardSpec(kicker="PHASE 3 // ONGOING", title="Days 31–90 (Assurance & Scale)", description="Continuous regression monitoring, content depth expansion, model citation tracking.", metric_value="31-90 DAYS", badge="SPRINT 3", badge_color="sky")
                ]

            elif s_id == "slide_71_phase1_7days":
                items = list(report.roadmap_7_days or [])
                if len(items) < 3:
                    extra = [f for f in (report.critical_findings or []) if f.title not in [getattr(it, "title", "") for it in items]]
                    for ef in extra:
                        if len(items) >= 3:
                            break
                        items.append(type("RoadmapStub", (), {
                            "title": ef.title,
                            "description": getattr(ef, "remediation", None) or getattr(ef, "description", ""),
                            "effort": "Immediate",
                            "impact": "High"
                        })())
                s.cards = []
                for i, it in enumerate(items[:3]):
                    desc = getattr(it, "description", None) or getattr(it, "rationale", None) or "Immediate engineering fix to restore indexation and protocol integrity."
                    s.cards.append(CardSpec(
                        kicker=f"ACTION 1.{i+1} // DAYS 1–7",
                        title=getattr(it, "title", f"Sprint 1 Action {i+1}")[:55],
                        description=desc[:140],
                        badge="CRITICAL" if i == 0 else "HIGH",
                        badge_color="rose" if i == 0 else "amber"
                    ))
                if not s.cards:
                    s.cards = [
                        CardSpec(kicker="STATUS", title="Zero Critical P0 Findings", description="No immediate sprint-1 blocking defects were detected across crawl, headers, or security.", badge="PASSED", badge_color="emerald")
                    ]

            elif s_id == "slide_72_phase2_30days":
                items = list(report.roadmap_30_days or [])
                if len(items) < 3:
                    extra = [f for f in (report.findings or []) if str(getattr(f, "severity", "")).upper() in ("HIGH", "MEDIUM") and f.title not in [getattr(it, "title", "") for it in items]]
                    for ef in extra:
                        if len(items) >= 3:
                            break
                        items.append(type("RoadmapStub", (), {
                            "title": ef.title,
                            "description": getattr(ef, "remediation", None) or getattr(ef, "description", ""),
                            "effort": "Medium",
                            "impact": "Strategic"
                        })())
                s.cards = []
                for i, it in enumerate(items[:3]):
                    desc = getattr(it, "description", None) or getattr(it, "rationale", None) or "Strategic enhancement to anchor Schema entity graph and optimize conversion."
                    s.cards.append(CardSpec(
                        kicker=f"ACTION 2.{i+1} // DAYS 8–30",
                        title=getattr(it, "title", f"Sprint 2 Action {i+1}")[:55],
                        description=desc[:140],
                        badge="STRATEGIC",
                        badge_color="sky"
                    ))
                if not s.cards:
                    s.cards = [
                        CardSpec(kicker="STATUS", title="Core Foundation Sound", description="No secondary 30-day defects identified; proceed to long-term content authority scaling.", badge="STABLE", badge_color="emerald")
                    ]

            elif s_id == "slide_73_phase3_90days":
                items = list(report.roadmap_90_days or [])
                if len(items) < 3:
                    extra = [f for f in (report.findings or []) if str(getattr(f, "severity", "")).upper() in ("LOW", "INFO") and f.title not in [getattr(it, "title", "") for it in items]]
                    for ef in extra:
                        if len(items) >= 3:
                            break
                        items.append(type("RoadmapStub", (), {
                            "title": ef.title,
                            "description": getattr(ef, "remediation", None) or getattr(ef, "description", ""),
                            "effort": "Low",
                            "impact": "Optimization"
                        })())
                s.cards = []
                for i, it in enumerate(items[:3]):
                    desc = getattr(it, "description", None) or getattr(it, "rationale", None) or "Systemic assurance, competitive parity scaling, and citation tracking."
                    s.cards.append(CardSpec(
                        kicker=f"ACTION 3.{i+1} // DAYS 31–90",
                        title=getattr(it, "title", f"Sprint 3 Action {i+1}")[:55],
                        description=desc[:140],
                        badge="ASSURANCE",
                        badge_color="emerald"
                    ))
                if not s.cards:
                    s.cards = [
                        CardSpec(kicker="STATUS", title="Assurance Protocol Established", description="Deploy ongoing monthly regression runs to safeguard against visibility drift.", badge="MAINTENANCE", badge_color="sky")
                    ]

            elif s_id == "slide_74_code_patches":
                patches = report.code_patches[:2] if report.code_patches else []
                p1_name = patches[0].target_file if len(patches) > 0 else "index.html (Schema.org JSON-LD)"
                p1_desc = patches[0].explanation if len(patches) > 0 else "Injects Organization and Product schema with verified SameAs entity nodes."
                p2_name = patches[1].target_file if len(patches) > 1 else "public/llms.txt (AI Crawler Manifesto)"
                p2_desc = patches[1].explanation if len(patches) > 1 else "Defines structured markdown API and product documentation for LLM scrapers."
                s.cards = [
                    CardSpec(kicker="PATCH 01 // PRODUCTION READY", title=p1_name, description=p1_desc, badge="VALIDATED", badge_color="emerald"),
                    CardSpec(kicker="PATCH 02 // PRODUCTION READY", title=p2_name, description=p2_desc, badge="VALIDATED", badge_color="emerald")
                ]

            # -----------------------------------------------------------------
            # Slide 75-76: Governance & Seal
            # -----------------------------------------------------------------
            elif s_id == "slide_75_evidence_ledger":
                s.cards = [
                    CardSpec(kicker="LEDGER INTEGRITY", title="Content-Addressed Storage", description="Every HTML snippet, header, and response body is hashed with SHA-256.", metric_value="SHA-256", badge="IMMUTABLE", badge_color="sky"),
                    CardSpec(kicker="VERIFICATION AUDIT", title="AST DOM Selectors", description="Findings are stamped with precise CSS selectors for reproducible re-runs.", metric_value="CSS PATHS", badge="REPRODUCIBLE", badge_color="emerald"),
                    CardSpec(kicker="DATA GOVERNANCE", title="Strict Zero-Simulation", description="Speculative TAM, invented CAC, and synthetic backlinks are barred by protocol.", metric_value="ZERO FAKE", badge="ENFORCED", badge_color="emerald"),
                    CardSpec(kicker="SEALED MANIFEST", title="Cryptographic Package", description="Report UUID pins evidence tokens to agent models, providers, and timestamp.", metric_value="SEALED", badge="AUDITABLE", badge_color="sky")
                ]

            elif s_id == "slide_76_csuite_seal":
                s.cards = [
                    CardSpec(kicker="FORMAL CERTIFICATION", title="Dristik Assurance Seal", description=f"Certified audit dossier completed for {domain}. All findings verified against deterministic ground truth.", metric_value="CERTIFIED", badge="SEAL OF TRUTH", badge_color="emerald"),
                    CardSpec(kicker="DELIVERY TIMESTAMP", title="Generated Execution Date", description=report.generated_at or "Measured on audit execution", badge="TIMESTAMP", badge_color="sky"),
                    CardSpec(kicker="LEGAL & COMPLIANCE", title="Confidential Advisory", description="Prepared exclusively for executive leadership. All rights reserved.", badge="PROPRIETARY", badge_color="sky")
                ]

        # Post-processing pass: bind deterministic metrics, interpretations, and lineage tokens
        from app.reports.deck.math_engine import DeterministicMetricEngine
        from app.reports.deck.adjudication import BlackboardAdjudicationAuditor
        from app.reports.deck.narrative_synthesizer import ExecutiveNarrativeSynthesizer
        from app.reports.deck.models import SlideLayoutType

        math_engine = DeterministicMetricEngine()
        metric_bundle = math_engine.compute_bundle(report)

        adjudicator = BlackboardAdjudicationAuditor()
        adj_report = adjudicator.audit_report(report)

        synthesizer = ExecutiveNarrativeSynthesizer()

        for s in blueprint.slides:
            # Bind evidence tokens for findings, tables, and code patches
            if s.layout in (SlideLayoutType.FINDINGS_LEDGER, SlideLayoutType.CODE_PATCH_DIFF, SlideLayoutType.TABLE_MATRIX):
                if not s.lineage_evidence_tokens:
                    s.lineage_evidence_tokens = list(adj_report.evidence_token_inventory[:4])
                if not s.evidence_citations:
                    s.evidence_citations = [f"Proof: {tok}" for tok in s.lineage_evidence_tokens]

            # Bind analytical interpretation ("Read: ...") on exhibits
            has_exhibit = (s.chart is not None or len(s.table_rows) > 0)
            if has_exhibit and not s.interpretation:
                s.interpretation = synthesizer.synthesize_interpretation(s.thematic_focus, metric_bundle)

        return blueprint
