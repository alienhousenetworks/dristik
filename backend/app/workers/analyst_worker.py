"""
Dristik AI Cognitive Analyst Worker - Enterprise Consulting Tier
Reusable specialist worker executing deep evaluations across Commercial Strategy, GEO, Content Authority, and UX/CRO.
"""
from typing import Dict, Any, Optional
from app.workers.base_worker import BaseCognitiveWorker
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import BusinessProfile
from app.domain.enums import Category, Severity, BusinessIntent

class CognitiveAnalystWorker(BaseCognitiveWorker):
    def __init__(self, worker_id: str, model_router):
        super().__init__(worker_id=worker_id, role_name="Enterprise Strategy & Experience Analyst", model_router=model_router)

    async def execute_task(
        self,
        capability_id: str,
        blackboard: CognitiveBlackboard,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        evidence_list = blackboard.evidence_store.get_all()
        pages_summary = "\n".join([
            f"• Route: {p.url} | Title: {p.title or 'Untitled'} | H1: {', '.join(p.h1) if p.h1 else 'None'} | Words: {p.word_count} | Schema: {', '.join(p.schema_types) if p.schema_types else 'None'}"
            for p in blackboard.pages[:8]
        ])

        # 1. Commercial Strategy, Positioning, ICP & Differentiation
        if capability_id in ["12_positioning", "13_icp_alignment", "14_value_prop_strength", "15_commercial_clarity", "16_competitive_differentiation"]:
            prompt_contract = (
                "Conduct a commercial positioning audit from crawled evidence only:\n"
                "1. BUSINESS IDENTITY: Official brand name and a specific niche (who + offer). Never 'Technology' if a sharper label exists.\n"
                "2. ICP: Buyer role, org scale, pain. If the page says 'teams' or names no role, mark AMBIGUOUS. Do not invent CTO.\n"
                "3. 5-SECOND TEST: Score 80-95 only if H1 names buyer + offer + outcome. Slogans score 10-34. Score must match the band.\n"
                "4. MOTION: saas vs lead_generation vs ecommerce vs agency from CTAs, not from the word 'product' or 'platform'.\n"
                "5. MOAT: unknown unless evidence states IP, lock-in, network, or scale.\n"
                "6. CTAs: quote primary and secondary button text.\n"
                "7. CLAIMS: max 3, each with evidence_refs and BEFORE->AFTER only for strings that exist in evidence.\n"
                "Do not invent competitors, TAM, CAC, or traffic."
            )
            schema_desc = (
                "{\n"
                '  "business_name": "string",\n'
                '  "industry": "string",\n'
                '  "niche": "string",\n'
                '  "products": ["string"],\n'
                '  "services": ["string"],\n'
                '  "target_audience": "string",\n'
                '  "business_model": "string",\n'
                '  "value_proposition": "string",\n'
                '  "primary_intent": "saas | lead_generation | ecommerce | agency | media",\n'
                '  "primary_cta": "string",\n'
                '  "confidence": 0.95,\n'
                '  "claims": [\n'
                '    {\n'
                '      "statement": "Explicit diagnostic statement regarding positioning/ICP/differentiation",\n'
                '      "category": "COMPETITIVE | ON_PAGE_SEO | UX_CONVERSION",\n'
                '      "severity": "CRITICAL | HIGH | MEDIUM | LOW",\n'
                '      "confidence": 0.92,\n'
                '      "impact": 8,\n'
                '      "effort": 3,\n'
                '      "evidence_refs": ["ev_001"],\n'
                '      "recommendation": "Prescriptive executive solution with concrete BEFORE -> AFTER copy or positioning adjustments"\n'
                '    }\n'
                '  ]\n'
                "}"
            )
            
            user_site_type = getattr(blackboard, "user_declared_site_type", None)
            user_context = f"\nUSER-DECLARED BUSINESS CATEGORY / INTENT (GROUND TRUTH):\n{user_site_type}\n" if user_site_type else ""

            result = await self.model_router.generate_structured(
                capability="business_intelligence",
                agent_role="Principal commercial positioning auditor",
                task_contract=prompt_contract,
                evidence_list=evidence_list,
                rubric=(
                    "1. BRAND FIDELITY: Zero hallucination of company names or offerings. Verify against exact titles and DOM headers.\n"
                    "2. USER OVERRIDE: If USER-DECLARED BUSINESS CATEGORY is provided, treat it as verified ground truth authorization from the enterprise owner.\n"
                    "3. ICP SHARPNESS: Heavily penalize broad, vague target descriptions. Require specific commercial buyer personas.\n"
                    "4. DIFFERENTIATION TEST: Evaluate whether the value prop clearly answers 'Why choose this over alternatives?' without empty jargon.\n"
                    "5. SEVERITY BENCHMARK: Critical = Value proposition entirely incomprehensible; High = ICP misaligned or hidden monetization model; Medium = Unoptimized secondary CTA copy.\n"
                    "6. EVIDENCE BINDING: Every claim must cite verified evidence IDs [ev_xxx] or explicit page routes."
                ),
                output_schema_desc=schema_desc,
                additional_context=f"Multi-Page Crawl Topology:\n{pages_summary}{user_context}"
            )
            
            # Update Blackboard Business Profile
            if result.get("business_name") and result.get("business_name") not in ["Unknown", "Unknown Business"]:
                bp = blackboard.business_profile or BusinessProfile()
                bp.business_name = result.get("business_name", bp.business_name)
                bp.industry = result.get("industry", bp.industry)
                bp.niche = result.get("niche", bp.niche)
                bp.target_audience = result.get("target_audience", bp.target_audience)
                bp.value_proposition = result.get("value_proposition", bp.value_proposition)
                bp.business_model = result.get("business_model", bp.business_model)
                bp.primary_cta = result.get("primary_cta", bp.primary_cta)
                if result.get("products"):
                    bp.products = result.get("products")
                if result.get("services"):
                    bp.services = result.get("services")
                blackboard.business_profile = bp

            # Register Claims
            for cl in result.get("claims", []):
                cat = Category.COMPETITIVE if capability_id == "16_competitive_differentiation" else Category.ON_PAGE_SEO
                sev_str = str(cl.get("severity", "MEDIUM")).upper()
                sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.MEDIUM
                blackboard.claim_registry.register_claim(
                    agent_id=f"{self.worker_id}_{capability_id}",
                    statement=cl.get("statement", "Commercial positioning diagnostic finding"),
                    category=cat,
                    severity=sev,
                    confidence=float(cl.get("confidence", 0.90)),
                    impact=int(cl.get("impact", 7)),
                    effort=int(cl.get("effort", 3)),
                    evidence_refs=cl.get("evidence_refs", []),
                    recommendation=cl.get("recommendation", "Refine commercial value proposition and ICP messaging.")
                )
            return result

        # 2. Generative Engine Optimization (GEO) & Entity Graph
        elif capability_id in ["10_entity_graph", "22_direct_extractability", "23_information_gain", "24_summarizability", "25_citation_readiness"]:
            prompt_contract = (
                "Execute an exhaustive Generative Engine Optimization (GEO) diagnostic for modern AI answer engines "
                "(Perplexity Pro, ChatGPT Search, Google Gemini Overviews, Claude):\n"
                "1. DIRECT FACT EXTRACTABILITY: Are core company facts, capabilities, and pricing written in concise, self-contained declarative paragraphs (40-60 words) under clear semantic H2/H3 tags?\n"
                "2. INFORMATION GAIN: Does the site provide original proprietary statistics, benchmarks, or case studies versus regurgitated generic boilerplate?\n"
                "3. SCHEMA.ORG ENTITY GRAPH: Audit completeness of JSON-LD (Organization, WebSite, SoftwareApplication, Product, FAQPage) and sameAs authority linking (Wikidata, LinkedIn, Crunchbase).\n"
                "4. CITATION READINESS: Assess probability of capturing direct footnote citations in AI answer engine outputs for target buyer inquiries.\n"
                "5. HIGH-CONVICTION CLAIMS: Formulate 2-3 actionable GEO claims with concrete Schema.org JSON-LD snippets or copy restructuring directives."
            )
            schema_desc = (
                "{\n"
                '  "extractability_score": 75,\n'
                '  "information_gain_score": 70,\n'
                '  "citation_readiness_score": 68,\n'
                '  "entity_clarity_score": 72,\n'
                '  "claims": [\n'
                '    {\n'
                '      "statement": "Detailed diagnostic on AI answer extractability or missing Schema.org entity linking",\n'
                '      "category": "GEO",\n'
                '      "severity": "HIGH | MEDIUM | CRITICAL",\n'
                '      "confidence": 0.94,\n'
                '      "impact": 9,\n'
                '      "effort": 2,\n'
                '      "evidence_refs": ["ev_001"],\n'
                '      "recommendation": "Concrete Schema.org JSON-LD or copy restructure instructions for AI citation capture"\n'
                '    }\n'
                '  ]\n'
                "}"
            )
            result = await self.model_router.generate_structured(
                capability="geo_analysis",
                agent_role="Principal Director of Generative Engine Optimization (GEO) & Semantic AI Architecture",
                task_contract=prompt_contract,
                evidence_list=evidence_list,
                rubric=(
                    "1. KNOWLEDGE GRAPH BENCHMARK: Heavily penalize absence of structured Schema.org JSON-LD entity graph (< 40 score).\n"
                    "2. AI SCRAPING ACCESSIBILITY: Deduct points when key factual offerings are buried in unindexed client JS or ambiguous marketing jargon.\n"
                    "3. CITATION READINESS: High citation scores (80+) require structured FAQ blocks, clear semantic heading hierarchy (H1->H2->H3), and concise factual definitions.\n"
                    "4. EVIDENCE GROUNDING: Every audit claim must cite explicit evidence IDs [ev_xxx] from page DOM or crawl artifacts."
                ),
                output_schema_desc=schema_desc,
                additional_context=f"Multi-Page Crawl Topology:\n{pages_summary}"
            )
            for cl in result.get("claims", []):
                sev_str = str(cl.get("severity", "MEDIUM")).upper()
                sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.MEDIUM
                blackboard.claim_registry.register_claim(
                    agent_id=f"{self.worker_id}_{capability_id}",
                    statement=cl.get("statement", "GEO and AI discoverability diagnostic claim"),
                    category=Category.GEO,
                    severity=sev,
                    confidence=float(cl.get("confidence", 0.92)),
                    impact=int(cl.get("impact", 8)),
                    effort=int(cl.get("effort", 2)),
                    evidence_refs=cl.get("evidence_refs", []),
                    recommendation=cl.get("recommendation", "Structure answers with explicit Schema.org JSON-LD entity markup and direct answer paragraphs.")
                )
            return result

        # 3. Content Depth, Topic Coverage & E-E-A-T Authority
        elif capability_id in ["17_content_depth", "18_eeat_authority", "20_topic_coverage"]:
            prompt_contract = (
                "Audit the content depth, topical authority, and Google E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness):\n"
                "1. TOPICAL DEPTH & THIN CONTENT RISKS: Analyze word count, heading hierarchy (H1->H2->H3), topic completeness, and thin content vulnerabilities across key pages.\n"
                "2. E-E-A-T PROOF SIGNALS: Audit verified proof points—author credentials, client case studies, data-backed claims, and expert authorship citations.\n"
                "3. TOPICAL GAPS & BUYER OBJECTIONS: Identify high-intent buyer questions, comparison queries (e.g. '[Brand] vs [Competitor]'), and unaddressed objections missing from the domain.\n"
                "4. HIGH-CONVICTION CLAIMS: Formulate 2-3 specific findings with actionable copy expansion and authority signal implementations."
            )
            schema_desc = (
                "{\n"
                '  "claims": [\n'
                '    {\n'
                '      "statement": "Content authority or depth assessment",\n'
                '      "category": "CONTENT",\n'
                '      "severity": "HIGH | MEDIUM | LOW",\n'
                '      "confidence": 0.90,\n'
                '      "impact": 7,\n'
                '      "effort": 4,\n'
                '      "evidence_refs": ["ev_001"],\n'
                '      "recommendation": "Actionable content expansion and authority signal implementation"\n'
                '    }\n'
                '  ]\n'
                "}"
            )
            result = await self.model_router.generate_structured(
                capability="content_analysis",
                agent_role="Executive Director of Editorial Content Architecture & Google E-E-A-T Authority",
                task_contract=prompt_contract,
                evidence_list=evidence_list,
                rubric=(
                    "1. DEPTH THRESHOLD: Flag pages under 300 words as thin content risk unless intentionally minimalist transactional landing pages.\n"
                    "2. VERIFIABLE PROOF: Require demonstrable evidence of expertise (metrics, real client logos, customer outcomes) rather than unsupported assertions.\n"
                    "3. READABILITY CALIBRATION: Evaluate Flesch Reading Ease; balance executive professional tone with skimmable formatting (bullet points, clear subheads).\n"
                    "4. EVIDENCE GROUNDING: Cite verified evidence IDs [ev_xxx] or page URLs."
                ),
                output_schema_desc=schema_desc,
                additional_context=f"Multi-Page Crawl Topology:\n{pages_summary}"
            )
            for cl in result.get("claims", []):
                sev_str = str(cl.get("severity", "MEDIUM")).upper()
                sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.MEDIUM
                blackboard.claim_registry.register_claim(
                    agent_id=f"{self.worker_id}_{capability_id}",
                    statement=cl.get("statement", f"{capability_id} diagnostic finding"),
                    category=Category.CONTENT,
                    severity=sev,
                    confidence=float(cl.get("confidence", 0.89)),
                    impact=int(cl.get("impact", 7)),
                    effort=int(cl.get("effort", 3)),
                    evidence_refs=cl.get("evidence_refs", []),
                    recommendation=cl.get("recommendation", "Deepen topical coverage and embed verifiable authority proof points.")
                )
            return result

        # 4. User Experience, CRO & Trust Signals
        elif capability_id in ["31_ux_friction", "32_trust_signals", "33_conversion_cro"]:
            prompt_contract = (
                "Conduct an executive Conversion Rate Optimization (CRO), UX friction, and Trust Signal audit:\n"
                "1. PRIMARY CTA ARCHITECTURE: Audit primary CTA visibility, contrast, descriptive action labeling, and placement above the fold and at key cognitive decision moments.\n"
                "2. COGNITIVE FRICTION: Identify user journey hurdles, unclear next steps, form fatigue, and layout confusion that degrade conversion velocity.\n"
                "3. TRUST BADGING & RISK REVERSALS: Inspect security badges, SOC2/ISO/GDPR compliance statements, customer testimonials, client logos, and contact transparency.\n"
                "4. MOBILE & VISUAL SCANNING: Assess readability, visual hierarchy, and mobile usability indicators.\n"
                "5. CONVERSION FINDINGS: Formulate 2-3 high-impact conversion friction findings with direct UI/UX solutions."
            )
            schema_desc = (
                "{\n"
                '  "claims": [\n'
                '    {\n'
                '      "statement": "UX friction or CRO conversion bottleneck finding",\n'
                '      "category": "UX_CONVERSION",\n'
                '      "severity": "HIGH | MEDIUM | CRITICAL",\n'
                '      "confidence": 0.91,\n'
                '      "impact": 8,\n'
                '      "effort": 3,\n'
                '      "evidence_refs": ["ev_001"],\n'
                '      "recommendation": "Direct UI/UX remediation to eliminate drop-off and maximize lead velocity"\n'
                '    }\n'
                '  ]\n'
                "}"
            )
            result = await self.model_router.generate_structured(
                capability="ux_conversion",
                agent_role="Principal Conversion Rate Optimization (CRO) Architect & Behavioral UX Scientist",
                task_contract=prompt_contract,
                evidence_list=evidence_list,
                rubric=(
                    "1. CONVERSION FOCUS: Prioritize blockers directly causing drop-off on primary conversion funnels.\n"
                    "2. CTA CLARITY: Flag generic, passive, or hidden CTA buttons (e.g. 'Submit', 'Learn More') as HIGH severity.\n"
                    "3. TRUST DEFICIT: Flag absence of verifiable social proof, security credentials, or clear contact details as MEDIUM/HIGH severity.\n"
                    "4. PRESCRIPTIVE REMEDIATION: Recommendations must include specific visual, copy, or structural UI changes.\n"
                    "5. EVIDENCE GROUNDING: Cite verified evidence IDs [ev_xxx] or explicit page selectors."
                ),
                output_schema_desc=schema_desc,
                additional_context=f"Multi-Page Crawl Topology:\n{pages_summary}"
            )
            for cl in result.get("claims", []):
                sev_str = str(cl.get("severity", "MEDIUM")).upper()
                sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.MEDIUM
                blackboard.claim_registry.register_claim(
                    agent_id=f"{self.worker_id}_{capability_id}",
                    statement=cl.get("statement", f"{capability_id} conversion finding"),
                    category=Category.UX_CONVERSION,
                    severity=sev,
                    confidence=float(cl.get("confidence", 0.90)),
                    impact=int(cl.get("impact", 8)),
                    effort=int(cl.get("effort", 3)),
                    evidence_refs=cl.get("evidence_refs", []),
                    recommendation=cl.get("recommendation", "Optimize CTA hierarchy and introduce high-visibility trust credentials.")
                )
            return result

        return {}
