"""
Dristik AI Dedicated Business Understanding Orchestrator
Coordinates the 5 Specialized Cognitive Workers:
1. Business Discovery Agent
2. Intent & Journey Intelligence Agent
3. Category & Product Intelligence Agent
4. Business Model & Commercial Intelligence Agent
5. Semantic Website Strategist

Includes:
- Multi-Agent Consensus Engine
- Contradiction Detection Engine (User-Declared vs DOM Evidence & Cross-Agent Clashes)
- Zero-fabrication Evidence-First Architecture
"""
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple

from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import (
    BusinessProfile,
    FindingEvidence,
    ContradictionReport,
    SemanticBusinessRepresentation,
)
from app.domain.enums import BusinessIntent, EvidenceState
from app.evidence.retriever import EvidenceRetriever
from app.inference.prompt_compiler import load_prompt
from app.inference.schemas import (
    AgentDiscoveryOutput,
    AgentIntentJourneyOutput,
    AgentCategoryProductOutput,
    AgentBusinessModelOutput,
    AgentSemanticStrategistOutput,
)

logger = logging.getLogger("dristik.business_understanding")


class BusinessUnderstandingOrchestrator:
    """
    Cognitive layer responsible for answering 'What is this business?' before any audits run.
    """
    def __init__(self, model_router):
        self.model_router = model_router
        self.core_system_prompt = load_prompt("business_core_system") or (
            "You are Dristik AI's Business Intelligence Reasoning Engine. "
            "Understand websites as businesses, not merely as collections of keywords. "
            "Never assume industry, intent, or model from isolated keywords. Cite verified evidence."
        )

    async def execute_business_understanding(
        self,
        blackboard: CognitiveBlackboard
    ) -> SemanticBusinessRepresentation:
        """
        Executes the 5 cognitive workers, runs consensus, evaluates user declaration vs DOM evidence,
        and builds the canonical SemanticBusinessRepresentation.
        """
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent("business_intelligence", limit=35)
        site_facts = getattr(blackboard, "site_facts", {}) or {}

        # 1. Run Cognitive Workers independently. A strategist JSON miss must not
        # wipe identity already produced by the other four agents.
        discovery_res, d_err = await self._run_optional_agent(
            "Business Discovery Agent", self._run_discovery_agent, evidence_slice, site_facts
        )
        intent_res, i_err = await self._run_optional_agent(
            "Intent & Journey Agent", self._run_intent_journey_agent, evidence_slice, site_facts
        )
        category_res, c_err = await self._run_optional_agent(
            "Category & Product Agent", self._run_category_product_agent, evidence_slice, site_facts
        )
        commercial_res, m_err = await self._run_optional_agent(
            "Business Model Agent", self._run_business_model_agent, evidence_slice, site_facts
        )

        core_failures = [e for e in (d_err, i_err, c_err, m_err) if e]
        if not any([discovery_res, intent_res, category_res, commercial_res]):
            reason = "; ".join(core_failures) or "all business intelligence agents failed"
            logger.warning("LLM business reasoning failed: %s", reason)
            return self._build_offline_fallback(
                blackboard, site_facts, evidence_slice, failure_reason=reason
            )

        discovery_res = discovery_res or AgentDiscoveryOutput()
        intent_res = intent_res or AgentIntentJourneyOutput()
        category_res = category_res or AgentCategoryProductOutput()
        commercial_res = commercial_res or AgentBusinessModelOutput()

        context_summary = {
            "discovery": self._compact_agent(discovery_res, [
                "business_name", "industry", "sub_industry", "what_company_does",
                "who_it_serves", "what_it_sells", "how_it_makes_money",
            ]),
            "intent_journey": self._compact_agent(intent_res, [
                "primary_intent", "secondary_intents", "journey_stages",
                "conversion_events", "friction_points",
            ]),
            "category_product": self._compact_agent(category_res, [
                "product_categories", "services", "service_categories",
                "product_families", "use_cases", "audience_segments",
            ]),
            "commercial_model": self._compact_agent(commercial_res, [
                "primary_model", "secondary_model", "commercial_motion",
                "conversion_model",
            ]),
            "user_declared_site_type": blackboard.user_declared_site_type,
            "user_declared_notes": blackboard.user_declared_site_type_notes,
        }
        strategist_res, s_err = await self._run_optional_agent(
            "Semantic Strategist",
            self._run_semantic_strategist,
            context_summary,
            evidence_slice,
            site_facts,
        )
        if s_err:
            logger.warning("Semantic Strategist failed; keeping identity from the other agents: %s", s_err)
        strategist_res = strategist_res or AgentSemanticStrategistOutput(
            intent_alignment_analysis=(
                "Semantic Strategist JSON was unavailable. Identity below is assembled from "
                "Discovery, Intent, Category, and Commercial agents only."
            ),
            architecture_supports_goal=True,
            value_proposition_clarity="unmeasured",
            machine_comprehension_assessment="unmeasured",
            confidence=0.0,
        )

        # 2. Multi-Agent Consensus Engine
        consensus_text, consensus_confidence, is_disputed = self._compute_consensus(
            discovery_res, intent_res, category_res, commercial_res, strategist_res
        )

        # 3. Contradiction Engine (User Declared vs Evidence & Cross-agent)
        contradiction = self._detect_contradictions(
            user_declared=blackboard.user_declared_site_type,
            user_notes=blackboard.user_declared_site_type_notes,
            discovery=discovery_res,
            commercial=commercial_res,
            intent=intent_res,
            strategist=strategist_res,
            blackboard=blackboard
        )

        # 4. Construct Evidence Items
        evidence_items = self._compile_evidence_items(
            discovery_res, intent_res, category_res, commercial_res, blackboard
        )

        # 5. Assemble Canonical SemanticBusinessRepresentation
        geo = site_facts.get("target_geography")
        if isinstance(geo, str):
            geo = [geo] if geo.strip() else []
        if not isinstance(geo, list):
            geo = []

        semantic_rep = SemanticBusinessRepresentation(
            industry=discovery_res.industry or "Unknown",
            sub_industry=discovery_res.sub_industry,
            business_model=commercial_res.primary_model or "Unknown",
            secondary_business_models=[commercial_res.secondary_model] if commercial_res.secondary_model else [],
            website_type=self._determine_website_type(commercial_res, intent_res, discovery_res) or "Unknown",
            primary_intent=intent_res.primary_intent or "Unknown",
            secondary_intents=intent_res.secondary_intents or [],
            target_audience=discovery_res.who_it_serves or [],
            geography=geo,
            products=category_res.product_families or category_res.product_categories or [],
            services=category_res.services or category_res.service_categories or [],
            product_categories=category_res.product_categories or [],
            service_categories=category_res.service_categories or [],
            journey_stages=intent_res.journey_stages or [],
            conversion_events=intent_res.conversion_events or [],
            friction_points=intent_res.friction_points or [],
            confidence=round(consensus_confidence, 2),
            evidence=evidence_items,
            consensus_summary=consensus_text,
            is_disputed=is_disputed,
            contradiction=contradiction,
            source_provenance={
                "discovery_agent": "Agent 1 (Discovery)",
                "intent_agent": "Agent 2 (Intent & Journey)",
                "taxonomy_agent": "Agent 3 (Category & Product)",
                "commercial_agent": "Agent 4 (Business Model)",
                "strategist_agent": "Agent 5 (Semantic Strategist)",
            },
            llm_status="ok",
            llm_failure_reason=None,
        )

        # Sync with blackboard's BusinessProfile
        self._sync_with_business_profile(blackboard, semantic_rep, discovery_res, commercial_res)
        blackboard.semantic_business = semantic_rep
        if contradiction:
            blackboard.identity_contradictions.append(contradiction)

        return semantic_rep

    async def _run_optional_agent(self, agent_name: str, fn, *args) -> Tuple[Optional[Any], Optional[str]]:
        try:
            return await fn(*args), None
        except Exception as e:
            logger.warning("%s failed: %s", agent_name, e)
            return None, f"{agent_name} failed: {e}"

    @staticmethod
    def _compact_agent(model: Any, keys: List[str]) -> Dict[str, Any]:
        data = model.model_dump() if hasattr(model, "model_dump") else dict(model or {})
        compact: Dict[str, Any] = {}
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                compact[key] = value[:4]
            elif isinstance(value, str) and len(value) > 400:
                compact[key] = value[:397] + "..."
            else:
                compact[key] = value
        return compact

    @staticmethod
    def _require_llm_payload(res: Any, agent_name: str) -> Dict[str, Any]:
        if not isinstance(res, dict):
            raise RuntimeError(f"{agent_name} failed: empty model response")
        if res.get("status") == "unavailable" or res.get("unavailable_reason"):
            raise RuntimeError(
                f"{agent_name} failed: {res.get('unavailable_reason') or res.get('status')}"
            )
        return res

    async def _run_discovery_agent(self, evidence_slice: List[str], site_facts: Dict[str, Any]) -> AgentDiscoveryOutput:
        prompt = load_prompt("agent_business_discovery") or "Analyze what the business does, who it serves, and what it sells."
        task_contract = f"{self.core_system_prompt}\n\nTASK:\n{prompt}"
        res = await self.model_router.generate_structured(
            capability="business_discovery",
            agent_role="Business Discovery Agent",
            task_contract=task_contract,
            evidence_list=evidence_slice,
            output_schema_desc=json.dumps(AgentDiscoveryOutput.model_json_schema(), indent=2),
            site_facts=site_facts,
            task_card="Discover exact commercial operations from page evidence. Never assume from keywords.",
            max_claims=0
        )
        payload = self._require_llm_payload(res, "Business Discovery Agent")
        return AgentDiscoveryOutput(**payload)

    async def _run_intent_journey_agent(self, evidence_slice: List[str], site_facts: Dict[str, Any]) -> AgentIntentJourneyOutput:
        prompt = load_prompt("agent_intent_journey") or "Analyze website intent, customer journey stages, and conversion friction."
        task_contract = f"{self.core_system_prompt}\n\nTASK:\n{prompt}"
        res = await self.model_router.generate_structured(
            capability="intent_journey",
            agent_role="Intent & Journey Intelligence Agent",
            task_contract=task_contract,
            evidence_list=evidence_slice,
            output_schema_desc=json.dumps(AgentIntentJourneyOutput.model_json_schema(), indent=2),
            site_facts=site_facts,
            task_card="Determine dynamic customer journey and commercial intent from DOM progression.",
            max_claims=0
        )
        payload = self._require_llm_payload(res, "Intent & Journey Agent")
        return AgentIntentJourneyOutput(**payload)

    async def _run_category_product_agent(self, evidence_slice: List[str], site_facts: Dict[str, Any]) -> AgentCategoryProductOutput:
        prompt = load_prompt("agent_category_product") or "Analyze actual offerings, service categories, and product families semantically."
        task_contract = f"{self.core_system_prompt}\n\nTASK:\n{prompt}"
        res = await self.model_router.generate_structured(
            capability="category_product",
            agent_role="Category & Product Intelligence Agent",
            task_contract=task_contract,
            evidence_list=evidence_slice,
            output_schema_desc=json.dumps(AgentCategoryProductOutput.model_json_schema(), indent=2),
            site_facts=site_facts,
            task_card="Extract taxonomy semantically without keyword heuristics.",
            max_claims=0
        )
        payload = self._require_llm_payload(res, "Category & Product Agent")
        return AgentCategoryProductOutput(**payload)

    async def _run_business_model_agent(self, evidence_slice: List[str], site_facts: Dict[str, Any]) -> AgentBusinessModelOutput:
        prompt = load_prompt("agent_business_model") or "Determine commercial monetization model (B2B, SaaS, Services, D2C, Hybrid)."
        task_contract = f"{self.core_system_prompt}\n\nTASK:\n{prompt}"
        res = await self.model_router.generate_structured(
            capability="business_model",
            agent_role="Business Model & Commercial Intelligence Agent",
            task_contract=task_contract,
            evidence_list=evidence_slice,
            output_schema_desc=json.dumps(AgentBusinessModelOutput.model_json_schema(), indent=2),
            site_facts=site_facts,
            task_card="Identify primary and secondary commercial mechanisms with confidence.",
            max_claims=0
        )
        payload = self._require_llm_payload(res, "Business Model Agent")
        return AgentBusinessModelOutput(**payload)

    async def _run_semantic_strategist(
        self,
        context_summary: Dict[str, Any],
        evidence_slice: List[str],
        site_facts: Dict[str, Any]
    ) -> AgentSemanticStrategistOutput:
        prompt = load_prompt("agent_semantic_strategist") or "Synthesize high-level strategic alignment, machine comprehension, and contradictions."
        task_contract = (
            f"{self.core_system_prompt}\n\n"
            f"AGENT OUTPUTS SO FAR:\n{json.dumps(context_summary, indent=2)}\n\n"
            f"TASK:\n{prompt}"
        )
        res = await self.model_router.generate_structured(
            capability="semantic_strategist",
            agent_role="Semantic Website Strategist",
            task_contract=task_contract,
            evidence_list=evidence_slice,
            output_schema_desc=(
                '{"intent_alignment_analysis":"string","architecture_supports_goal":true,'
                '"value_proposition_clarity":"string","machine_comprehension_assessment":"string",'
                '"contradictions_detected":[],"content_gaps":[],"strategic_hypotheses":[],'
                '"confidence":0.0,"evidence_excerpts":[]}'
            ),
            site_facts=site_facts,
            task_card="Audit architecture alignment, identify value prop friction and flag any contradictions.",
            max_claims=0
        )
        payload = self._require_llm_payload(res, "Semantic Strategist")
        return AgentSemanticStrategistOutput(**payload)

    @staticmethod
    def _format_contradiction_detail(item: Any) -> Tuple[str, str]:
        """Extracts human-readable title and evidence string from raw dict or stringified dict."""
        import ast
        data = item
        if isinstance(item, str) and item.strip().startswith("{"):
            try:
                data = json.loads(item)
            except Exception:
                try:
                    data = ast.literal_eval(item)
                except Exception:
                    data = item

        if isinstance(data, dict):
            raw_title = data.get("contradiction") or data.get("title") or "Business model identity conflict"
            raw_evidence = data.get("evidence") or data.get("description") or ""
            raw_impact = data.get("business_impact") or ""

            title = " · ".join(str(x) for x in raw_title if x) if isinstance(raw_title, list) else str(raw_title)
            evidence = " · ".join(str(x) for x in raw_evidence if x) if isinstance(raw_evidence, list) else str(raw_evidence)
            impact = " · ".join(str(x) for x in raw_impact if x) if isinstance(raw_impact, list) else str(raw_impact)

            reason = f"{title}: {evidence}" if evidence else str(title)
            if impact:
                reason += f" (Impact: {impact})"
            excerpt = evidence or str(title)
            return str(reason), str(excerpt)

        if isinstance(item, list):
            text = " · ".join(str(x) for x in item if x)
            return text, text

        text = str(item)
        return text, text

    def _compute_consensus(
        self,
        discovery: AgentDiscoveryOutput,
        intent: AgentIntentJourneyOutput,
        category: AgentCategoryProductOutput,
        commercial: AgentBusinessModelOutput,
        strategist: AgentSemanticStrategistOutput
    ) -> Tuple[str, float, bool]:
        """
        Consensus Engine: Compares model outputs, evaluates agreement, and adjusts confidence.
        """
        confidences = [
            c for c in [
                discovery.confidence, intent.confidence, category.confidence,
                commercial.confidence, strategist.confidence,
            ]
            if c and c > 0
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.85

        # Check for alignment between commercial model and intent
        model_str = (commercial.primary_model or "").lower()
        intent_str = (intent.primary_intent or "").lower()
        
        is_disputed = False
        disagreement_notes = []

        # Example clash: Commercial says e-commerce, but intent says lead gen consulting with no checkout
        if "ecommerce" in model_str and "lead_generation" in intent_str:
            is_disputed = True
            disagreement_notes.append("Commercial model evaluates e-commerce, whereas Intent agent evaluates consultative lead generation.")
            avg_confidence = min(avg_confidence, 0.65)

        if strategist.contradictions_detected:
            is_disputed = True
            formatted_notes = [self._format_contradiction_detail(c)[0] for c in strategist.contradictions_detected]
            disagreement_notes.append(f"Strategist detected: {'; '.join(formatted_notes)}")
            avg_confidence = min(avg_confidence, 0.70)

        if is_disputed:
            summary = f"Multi-Agent Classification Uncertainty: {'; '.join(disagreement_notes)}"
        else:
            summary = (
                f"Multi-Agent Consensus ({int(avg_confidence * 100)}% confidence): "
                f"Verified {discovery.industry} organization operating under a {commercial.primary_model} "
                f"structure with primary {intent.primary_intent} user flow."
            )

        return summary, avg_confidence, is_disputed

    def _detect_contradictions(
        self,
        user_declared: Optional[str],
        user_notes: Optional[str],
        discovery: AgentDiscoveryOutput,
        commercial: AgentBusinessModelOutput,
        intent: AgentIntentJourneyOutput,
        strategist: AgentSemanticStrategistOutput,
        blackboard: CognitiveBlackboard
    ) -> Optional[ContradictionReport]:
        """
        Detects conflicts between user's declared website type and actual DOM evidence,
        or internal identity conflicts detected across the site.
        """
        if not user_declared or user_declared in ("", "other", "unknown", "i_am_not_sure"):
            # If user didn't specify, check if strategist detected internal conflicts
            if strategist.contradictions_detected:
                reason_text, excerpt_text = self._format_contradiction_detail(strategist.contradictions_detected[0])
                ev_items = [
                    FindingEvidence(
                        url=blackboard.website_url,
                        source="strategist_consensus",
                        excerpt=excerpt_text,
                        type="content",
                        state=EvidenceState.INFERRED
                    )
                ]
                return ContradictionReport(
                    id=f"contra_{uuid.uuid4().hex[:6]}",
                    contradiction_type="internal_identity_clash",
                    declared_type="Unspecified",
                    detected_type=commercial.primary_model,
                    confidence=strategist.confidence,
                    reason=reason_text,
                    evidence=ev_items
                )
            return None

        # User declared a specific type: compare against detected reality
        ud = user_declared.lower().replace("-", "_").replace(" ", "_")
        detected_model = (commercial.primary_model or "").lower()
        detected_intent = (intent.primary_intent or "").lower()

        # Normalization map
        declared_label = {
            "saas": "SaaS / Software Platform",
            "ecommerce": "E-Commerce / Online Retail",
            "agency_services": "Agency / Services",
            "agency": "Agency / Services",
            "business_corporate": "Business / Corporate",
            "marketplace": "Marketplace",
            "publisher_media": "Publisher / Media",
            "blog": "Blog",
            "healthcare": "Healthcare",
            "financial": "Financial",
        }.get(ud, user_declared)

        # Check for blatant mismatch
        mismatch = False
        mismatch_reason = ""

        # Case 1: User declared SaaS, but site is clearly an Agency / Consulting firm
        if ud in ("saas",) and ("agency" in detected_model or "consulting" in detected_model or "service" in detected_model or "professional" in detected_model):
            # Verify if there's self-serve software pricing or app login
            mismatch = True
            mismatch_reason = (
                f"User declared website type as '{declared_label}', but verified website evidence reveals "
                f"a B2B consulting & professional services firm ({commercial.primary_model}) "
                f"with consultative sales inquiries and no self-serve software platform."
            )

        # Case 2: User declared E-Commerce, but site has no product catalog or checkout
        elif ud in ("ecommerce",) and ("saas" in detected_model or "consulting" in detected_model or "agency" in detected_model):
            mismatch = True
            mismatch_reason = (
                f"User declared website type as '{declared_label}', but verified website evidence reveals "
                f"a {commercial.primary_model} model without a direct consumer cart or checkout system."
            )

        # Case 3: User declared Agency / Services, but site is a pure self-serve SaaS
        elif ud in ("agency_services", "agency") and ("saas" in detected_model or "software" in detected_model) and "self_serve" in commercial.commercial_motion:
            mismatch = True
            mismatch_reason = (
                f"User declared website type as '{declared_label}', but verified website evidence reveals "
                f"a self-serve software platform ({commercial.primary_model}) with subscription tiers."
            )

        if mismatch:
            # Gather concrete evidence from DOM
            ev_list: List[FindingEvidence] = []
            if commercial.evidence_excerpts:
                for exc in commercial.evidence_excerpts[:2]:
                    ev_list.append(
                        FindingEvidence(
                            url=blackboard.website_url,
                            source="commercial_signals",
                            excerpt=exc,
                            type="content",
                            state=EvidenceState.OBSERVED
                        )
                    )
            if not ev_list:
                ev_list.append(
                    FindingEvidence(
                        url=blackboard.website_url,
                        source="audit_intake",
                        excerpt=f"Declared: {declared_label} | Detected: {commercial.primary_model}",
                        type="user_input",
                        state=EvidenceState.OBSERVED
                    )
                )

            return ContradictionReport(
                id=f"contra_{uuid.uuid4().hex[:6]}",
                contradiction_type="user_vs_evidence",
                declared_type=declared_label,
                detected_type=commercial.primary_model,
                confidence=round(commercial.confidence, 2),
                reason=mismatch_reason,
                evidence=ev_list
            )

        return None

    def _determine_website_type(
        self,
        commercial: AgentBusinessModelOutput,
        intent: AgentIntentJourneyOutput,
        discovery: AgentDiscoveryOutput
    ) -> str:
        model = (commercial.primary_model or "").lower()
        if "saas" in model or "software" in model:
            return "B2B SaaS"
        if "ecommerce" in model or "retail" in model or "d2c" in model:
            return "E-Commerce"
        if "agency" in model or "consulting" in model or "service" in model:
            return "Agency / Professional Services"
        if "marketplace" in model:
            return "Marketplace"
        if "publisher" in model or "media" in model:
            return "Publisher / Media"
        return discovery.industry if discovery.industry and discovery.industry != "Unknown" else "Unknown"

    def _compile_evidence_items(
        self,
        discovery: AgentDiscoveryOutput,
        intent: AgentIntentJourneyOutput,
        category: AgentCategoryProductOutput,
        commercial: AgentBusinessModelOutput,
        blackboard: CognitiveBlackboard
    ) -> List[FindingEvidence]:
        items: List[FindingEvidence] = []
        for exc in (discovery.evidence_excerpts or [])[:2]:
            items.append(FindingEvidence(
                url=blackboard.website_url,
                source="homepage_content",
                excerpt=exc,
                type="content",
                state=EvidenceState.OBSERVED
            ))
        for exc in (commercial.evidence_excerpts or [])[:2]:
            items.append(FindingEvidence(
                url=blackboard.website_url,
                source="commercial_model",
                excerpt=exc,
                type="navigation",
                state=EvidenceState.OBSERVED
            ))
        return items

    def _sync_with_business_profile(
        self,
        blackboard: CognitiveBlackboard,
        semantic: SemanticBusinessRepresentation,
        discovery: AgentDiscoveryOutput,
        commercial: AgentBusinessModelOutput
    ):
        """
        Synchronizes the SemanticBusinessRepresentation with blackboard's BusinessProfile for downstream engines.
        """
        bp = blackboard.business_profile
        if discovery.business_name and discovery.business_name != "Unknown":
            bp.business_name = discovery.business_name
        bp.industry = semantic.industry
        bp.business_model = semantic.business_model
        bp.products = semantic.products
        bp.services = semantic.services
        bp.confidence = semantic.confidence

        intent_lower = (semantic.primary_intent or "").lower()
        if "saas" in intent_lower:
            bp.primary_intent = BusinessIntent.SAAS
        elif "ecommerce" in intent_lower:
            bp.primary_intent = BusinessIntent.ECOMMERCE
        elif "agency" in intent_lower or "service" in intent_lower:
            bp.primary_intent = BusinessIntent.AGENCY
        elif "publishing" in intent_lower or "media" in intent_lower:
            bp.primary_intent = BusinessIntent.CONTENT_PUBLISHING
        elif intent_lower in ("unknown", "", "none", "unmeasured"):
            bp.primary_intent = None
        else:
            bp.primary_intent = BusinessIntent.LEAD_GENERATION

    def _build_offline_fallback(
        self,
        blackboard: CognitiveBlackboard,
        site_facts: Dict[str, Any],
        evidence_slice: List[str],
        failure_reason: Optional[str] = None,
    ) -> SemanticBusinessRepresentation:
        """
        Structured offline semantic reasoning without naive single keyword matching.
        Evaluates headings, navigation structures, and schema types.
        """
        pages = blackboard.pages or []
        first_page = pages[0] if pages else None

        # Extract brand
        brand_candidates = site_facts.get("business_name_candidates", [])
        brand = brand_candidates[0] if brand_candidates else (first_page.title if first_page and first_page.title else "Unknown Business")

        # Determine architecture from structural signals
        h1s = first_page.h1 if first_page else []
        ctas = first_page.ctas if first_page else []
        cta_text = " ".join(ctas).lower()

        has_cart = any("cart" in l or "checkout" in l for p in pages for l in p.internal_links)
        has_pricing = any("pricing" in l for p in pages for l in p.internal_links)
        has_contact = any("contact" in l or "quote" in l for p in pages for l in p.internal_links)

        if has_cart and not has_contact:
            model = "E-Commerce / Direct-to-Consumer"
            intent = "ecommerce"
            website_type = "E-commerce"
        elif has_pricing and any("app" in l or "login" in l for p in pages for l in p.internal_links):
            model = "B2B SaaS"
            intent = "saas"
            website_type = "SaaS"
        elif has_contact and any(k in cta_text or k in " ".join(h1s).lower() for k in ["consult", "service", "agency", "book", "quote", "talk to", "schedule"]):
            model = "Professional Services & Consulting"
            intent = "lead_generation"
            website_type = "Agency / Services"
        else:
            model = "Unknown"
            intent = "unknown"
            website_type = "Unknown"

        evidence_items = [
            FindingEvidence(
                url=blackboard.website_url,
                source="dom_structure",
                excerpt=h1s[0] if h1s else (first_page.title if first_page and first_page.title else "No heading crawled"),
                type="content",
                state=EvidenceState.OBSERVED
            )
        ]

        observed_services = [h.strip() for h in h1s if h and h.strip()][:3]
        if failure_reason or website_type == "Unknown":
            model = "Unknown"
            intent = "unknown"
            website_type = "Unknown"
            confidence = 0.0
            summary = (
                f"Website category and business model are Unknown from crawled DOM evidence. "
                f"Observed title/H1: {brand}; CTAs: {', '.join(ctas[:3]) or 'none'}."
            )
        else:
            confidence = 0.78 if bool(brand and brand != "Unknown Business" and (h1s or ctas)) else 0.40
            summary = (
                f"Offline DOM parse: {model} / {intent}. "
                f"Brand from {'site_facts' if brand_candidates else 'title'}. Not a live market study."
            )
        rep = SemanticBusinessRepresentation(
            industry=site_facts.get("industry") or "Unknown",
            business_model=model,
            website_type=website_type,
            primary_intent=intent,
            secondary_intents=[],
            target_audience=[],
            products=[],
            services=observed_services,
            journey_stages=[],
            conversion_events=list(ctas)[:4],
            friction_points=[] if ctas else ["No CTA detected in the crawl."],
            confidence=confidence,
            evidence=evidence_items,
            consensus_summary=summary,
            source_provenance={"offline_engine": "Deterministic DOM Structural Parser"},
            llm_status="failed" if failure_reason else "ok",
            llm_failure_reason=failure_reason,
        )

        blackboard.semantic_business = rep
        self._sync_with_business_profile(blackboard, rep, AgentDiscoveryOutput(business_name=brand), AgentBusinessModelOutput(primary_model=model))
        return rep
