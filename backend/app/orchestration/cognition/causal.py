"""
Dristik AI Causal Reasoning & Root-Cause Analysis Engine
Distinguishes deep architectural and commercial bottlenecks from superficial symptoms.
Maps causal chains:
Observed Symptoms -> Inferred Root Cause -> Business Consequence -> Prescribed Remediation -> Expected Mechanism -> Verification -> Projected Outcome.
"""
from typing import List, Dict, Any, Optional
from pydantic import Field
from app.domain.models import Claim, BusinessProfile, Finding, CausalDiagnosticChain
from app.domain.enums import Category, Severity


class CausalBottleneck(CausalDiagnosticChain):
    """Backward-compatible wrapper supporting both legacy and enterprise causal attributes."""

    @property
    def root_cause(self) -> str:
        return self.inferred_root_cause

    @property
    def downstream_symptoms(self) -> List[str]:
        return self.observed_symptoms

    @property
    def prescribed_intervention(self) -> str:
        return self.prescribed_remediation


class CausalReasoningEngine:
    """
    Infers causal relationships across multi-source evidence (claims, findings,
    crawl summary, AI search evaluations, competitor bake-off) to isolate primary bottlenecks.
    """

    def analyze_root_causes(
        self,
        claims: List[Claim],
        business_profile: BusinessProfile,
        findings: Optional[List[Finding]] = None,
        ai_search_evaluations: Optional[List[Any]] = None,
        competitor_bakeoff: Optional[Any] = None,
        crawl_summary: Optional[Dict[str, Any]] = None,
        observatory_records: Optional[List[Any]] = None,
        competitive_graph: Optional[Any] = None,
    ) -> List[CausalDiagnosticChain]:
        bottlenecks: List[CausalDiagnosticChain] = []
        all_findings = findings or []
        summary = crawl_summary or {}

        # -------------------------------------------------------------
        # Helper: Collect finding IDs matching criteria
        # -------------------------------------------------------------
        def find_ids(keywords: List[str], categories: Optional[List[Category]] = None) -> List[str]:
            matched: List[str] = []
            for f in all_findings:
                text = f"{f.title} {f.description or ''}".lower()
                cat_match = categories is None or f.category in categories
                if cat_match and any(k in text for k in keywords):
                    matched.append(f.finding_id)
            return matched

        # Categorize claims
        icp_claims = [c for c in claims if any(k in c.statement.lower() for k in ["icp", "target audience", "value proposition", "positioning", "messaging"])]
        cta_claims = [c for c in claims if any(k in c.statement.lower() for k in ["cta", "call to action", "conversion", "button", "funnel"])]
        schema_claims = [c for c in claims if any(k in c.statement.lower() for k in ["schema", "json-ld", "structured data", "entity"])]
        ai_claims = [c for c in claims if any(k in c.statement.lower() for k in ["ai search", "citation", "chatgpt", "perplexity", "geo"])]

        # -------------------------------------------------------------
        # 1. Root Cause: Entity Ambiguity & Commercial Definition Bottleneck
        # -------------------------------------------------------------
        entity_finding_ids = find_ids(["entity", "icp", "value proposition", "positioning", "answer", "citation", "geo", "pricing"], [Category.GEO, Category.AI_SEARCH, Category.COMPETITIVE, Category.CONTENT])
        has_entity_gap = bool(icp_claims or entity_finding_ids or (ai_search_evaluations and len(ai_search_evaluations) > 0) or observatory_records)

        if has_entity_gap:
            symptoms = []
            if icp_claims:
                symptoms.append(icp_claims[0].statement)
            else:
                symptoms.append("Homepage and product positioning use ambiguous, non-differentiated category descriptions")

            # Check AI search citations or observatory records if available
            if observatory_records:
                obs_total = len(observatory_records)
                obs_cited = sum(1 for r in observatory_records if getattr(r, "brand_cited", False))
                obs_engines = list(set(getattr(r, "engine_name", getattr(r, "engine_id", "unknown")) for r in observatory_records))
                symptoms.append(f"AI Retrieval Observatory: Brand cited on {obs_cited}/{obs_total} runs across {len(obs_engines)} engine(s)")
            elif ai_search_evaluations and len(ai_search_evaluations) > 0:
                cited_count = 0
                for q in ai_search_evaluations:
                    if getattr(q, "was_cited", False) or getattr(q, "is_cited", False):
                        cited_count += 1
                symptoms.append(f"AI search retrieval: Brand cited on {cited_count}/{len(ai_search_evaluations)} high-intent commercial buyer queries")
            else:
                symptoms.append("Commercial buyer-intent queries: low explicit answerability in crawled HTML")

            # Check competitor context
            if competitor_bakeoff:
                symptoms.append("Competitor intelligence: competing domains captured citations due to explicit comparison and category landing pages")

            bottlenecks.append(CausalBottleneck(
                bottleneck_id="causal_01_entity_commercial_clarity",
                title="Commercial Entity Ambiguity & AI Retrieval Blindness",
                primary_category=Category.GEO,
                observed_symptoms=symptoms,
                inferred_root_cause="The site's entity, ICP targeting, category taxonomy, and buyer question answers are insufficiently explicit for commercial search and LLM retrieval engines.",
                business_consequence="Generative answer engines (Perplexity, ChatGPT, Gemini) default to competitors who publish explicit structured solutions and comparative definitions, creating potential commercial discovery suppression (actual revenue impact not directly measured).",
                prescribed_remediation="Deploy dedicated `/solutions/...` and comparison pages with Schema.org Organization + SoftwareApplication markup and direct Q&A blocks.",
                expected_mechanism="Provides dense, citation-ready definitional passages that answer buyer questions directly with structured entity grounding.",
                verification_step="Targeted re-crawl verifies buyer questions are answered with >85% semantic answerability in rendered HTML.",
                external_verification="Re-test Perplexity and ChatGPT answer engine queries post-indexing to confirm brand citation.",
                projected_outcome="AI answer engine citation rate improves from initial baseline to >40% across commercial buyer queries.",
                severity=Severity.HIGH,
                confidence=0.94,
                contributing_finding_ids=entity_finding_ids[:6]
            ))

        # -------------------------------------------------------------
        # 2. Root Cause: Technical Server Response Latency & Crawl Budget Exhaustion
        # -------------------------------------------------------------
        ttfb = float(summary.get("avg_ttfb_ms", 0.0) or 0.0)
        perf_finding_ids = find_ids(["ttfb", "latency", "speed", "server response", "performance"], [Category.TECHNICAL_SEO])
        if ttfb > 1500 or perf_finding_ids:
            latency_label = f"{ttfb:.0f}ms" if ttfb > 0 else "elevated"
            bottlenecks.append(CausalBottleneck(
                bottleneck_id="causal_02_server_latency",
                title="High Server Response Latency & Crawl Budget Degradation",
                primary_category=Category.TECHNICAL_SEO,
                observed_symptoms=[
                    f"Measured average TTFB of {latency_label} exceeds Google's 800ms recommended threshold",
                    "Initial HTML document delivery stalls downstream rendering and crawler processing"
                ],
                inferred_root_cause="Uncached dynamic server-side page generation and absence of edge CDN caching.",
                business_consequence="Search engine crawlers throttle page indexing rate, Core Web Vitals rankings are penalized, and prospective buyers experience bounce-inducing load delays.",
                prescribed_remediation="Implement CDN edge page caching, enable modern transport protocols (HTTP/2 or HTTP/3), and optimize server-side database bottlenecks.",
                expected_mechanism="Caches rendered HTML at the edge, slashing time-to-first-byte to <600ms globally and freeing crawl budget.",
                verification_step="Live HTTP benchmark verifies TTFB < 800ms across all audited routes.",
                external_verification="Google CruX and field Core Web Vitals report 'Good' classification.",
                projected_outcome="Crawl indexing efficiency triples; first-fold bounce rate decreases 15-25%.",
                severity=Severity.HIGH if ttfb > 2500 else Severity.MEDIUM,
                confidence=0.92,
                contributing_finding_ids=perf_finding_ids[:4]
            ))

        # -------------------------------------------------------------
        # 3. Root Cause: Missing Machine Grounding (Structured Schema & Directives)
        # -------------------------------------------------------------
        schema_finding_ids = find_ids(["schema", "json-ld", "structured data", "organization", "microdata", "llms.txt"], [Category.SCHEMA, Category.GEO])
        if schema_claims or schema_finding_ids:
            bottlenecks.append(CausalBottleneck(
                bottleneck_id="causal_03_structured_grounding",
                title="Missing Machine-Readable Grounding (Schema & Bot Directives)",
                primary_category=Category.SCHEMA,
                observed_symptoms=[
                    "Absence or defect in Schema.org Organization, WebSite, and Service JSON-LD definitions",
                    "Lack of llms.txt structured context file for autonomous web agents"
                ],
                inferred_root_cause="Site relies exclusively on visual layout without structured machine-readable relational graphs.",
                business_consequence="Search engines cannot generate rich snippets or Knowledge Graph nodes; AI crawlers risk hallucinating corporate attributes.",
                prescribed_remediation="Inject validated Schema.org JSON-LD graphs with cryptographic sameAs social anchors and deploy a canonical `/llms.txt`.",
                expected_mechanism="Establishes unequivocal corporate entity authority in search indexes and LLM training corpora.",
                verification_step="Schema validator verifies zero syntax errors and 100% attribute resolution on all key templates.",
                external_verification="Google Search Console Rich Results report confirms structured data validation.",
                projected_outcome="Eligibility for rich search features and elimination of entity hallucinations.",
                severity=Severity.HIGH,
                confidence=0.95,
                contributing_finding_ids=schema_finding_ids[:5]
            ))

        # -------------------------------------------------------------
        # 4. Root Cause: Conversion Funnel Friction & Value Realization
        # -------------------------------------------------------------
        cro_finding_ids = find_ids(["cta", "call to action", "conversion", "form", "friction", "trust", "testimonial"], [Category.UX_CONVERSION, Category.TRUST_AUTHORITY])
        if cta_claims or cro_finding_ids:
            bottlenecks.append(CausalBottleneck(
                bottleneck_id="causal_04_conversion_friction",
                title="Buyer Self-Qualification Friction & Weak Conversion Architecture",
                primary_category=Category.UX_CONVERSION,
                observed_symptoms=[
                    "Primary Call-to-Action (CTA) hierarchy is ambiguous or competing with secondary links",
                    "Form friction or missing verifiable trust proof (client logos, compliance badges, transparent pricing)"
                ],
                inferred_root_cause="Conversion journey requires high cognitive effort from first-time visitors before establishing value.",
                business_consequence="High-intent organic and AI-referred visitors abandon without converting, lowering visitor-to-opportunity ROI.",
                prescribed_remediation="Establish a single primary CTA above the fold, streamline form inputs to <4 essential fields, and anchor hero fold with enterprise proof points.",
                expected_mechanism="Eliminates decision paralysis and enables rapid buyer self-qualification.",
                verification_step="DOM inspection verifies prominent high-contrast CTA within top 500px viewport and single-step form submission.",
                external_verification="Web analytics records a measurable increase in goal completion rate.",
                projected_outcome="15% to 30% increase in visitor-to-lead conversion rate.",
                severity=Severity.MEDIUM,
                confidence=0.88,
                contributing_finding_ids=cro_finding_ids[:5]
            ))

        # -------------------------------------------------------------
        # 5. Root Cause: Competitive Answerability & Cross-Site Displacement
        # -------------------------------------------------------------
        comp_finding_ids = find_ids(["competitor", "alternative", "comparison", "displacement", "bakeoff"], [Category.COMPETITIVE, Category.GEO, Category.AI_SEARCH])
        comp_matrix_rows = getattr(competitive_graph, "matrix_rows", []) if competitive_graph else []
        comp_losses = [r for r in comp_matrix_rows if getattr(r, "winning_entity", "") == "competitor"]

        if comp_losses or competitor_bakeoff or comp_finding_ids:
            comp_symptoms = []
            if comp_losses:
                for r in comp_losses[:3]:
                    comp_symptoms.append(f"Inquiry '{r.question_text}': Competitor wins because {r.why_winner_won}")
            elif competitor_bakeoff:
                comp_symptoms.append("Competitor bakeoff: rival domains captured direct citations on commercial comparison queries")
            else:
                comp_symptoms.append("Competing domains publish explicit comparison and pricing pages answering buyer inquiries")

            bottlenecks.append(CausalBottleneck(
                bottleneck_id="causal_05_competitive_displacement",
                title="Competitive Answer Engine Displacement & Comparison Gap",
                primary_category=Category.COMPETITIVE,
                observed_symptoms=comp_symptoms,
                inferred_root_cause="Competitors publish explicit comparison-oriented pages, structured pricing, and category definitions that directly satisfy generative answer engine retrieval vectors.",
                business_consequence="High-intent buyers evaluating category solutions are routed to competing software applications by generative answer engines.",
                prescribed_remediation="Publish dedicated comparative `/vs/[competitor]` matrix pages and structured `/pricing` tier definitions with SoftwareApplication JSON-LD.",
                expected_mechanism="Supplies LLMs with high-affinity comparative facts and explicit feature diffs, overturning competitor citation dominance.",
                verification_step="In-situ re-crawl verifies comparison tables and schema markup achieve 100% attribute resolution.",
                external_verification="Re-probe commercial buyer questions across Perplexity and ChatGPT after search indexation.",
                projected_outcome="Citation share on competitive buyer inquiries increases from 0% to >35%.",
                severity=Severity.HIGH if len(comp_losses) >= 2 else Severity.MEDIUM,
                confidence=0.91,
                contributing_finding_ids=comp_finding_ids[:5]
            ))

        return bottlenecks
