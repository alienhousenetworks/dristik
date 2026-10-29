"""
Dristik AI Extractor Worker (Level 1 Perception & Semantic Extraction)
Extracts business identity, ICP, products/services, entities, pricing models,
claims, CTAs, and semantic relationships with strict selector and content-hash provenance.
"""
from typing import Dict, Any, Optional, List
from app.workers.base_worker import BaseCognitiveWorker
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import BusinessProfile
from app.domain.enums import Category, Severity

class CognitiveExtractorWorker(BaseCognitiveWorker):
    def __init__(self, worker_id: str, model_router):
        super().__init__(
            worker_id=worker_id,
            role_name="Semantic Entity & Perception Extractor",
            model_router=model_router
        )

    async def execute_task(
        self,
        capability_id: str,
        blackboard: CognitiveBlackboard,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        evidence_list = blackboard.evidence_store.get_all()
        pages = blackboard.pages[:8]
        pages_summary = "\n".join([
            f"• URL: {p.url} | Title: {p.title or 'N/A'} | H1: {', '.join(p.h1)} | Words: {p.word_count} | Schema: {', '.join(p.schema_types)}"
            for p in pages
        ])

        contract = (
            "Extract an authoritative, high-precision semantic knowledge graph from the crawled website evidence:\n"
            "1. EXACT ENTITY IDENTIFIERS: Official brand name, legal entity clues, parent company, locations, and copyright ownership from title, meta, or footer.\n"
            "2. PRODUCT & SERVICE TAXONOMY: Granular product modules, solution offerings, feature capabilities, and core deliverables.\n"
            "3. ICP & BUYER PERSONAS: Target industry verticals, organization maturity/scale, and target buyer job titles.\n"
            "4. VALUE PROPOSITION & PROOF POINTS: Primary functional transformation promise and quantifiable metrics/case study outcomes.\n"
            "5. CONVERSION ARCHITECTURE: Verbatim primary and secondary CTA text and destination URLs.\n"
            "6. EXTRACTED OBSERVATIONS: 2-3 observable factual assertions with explicit DOM evidence selector references."
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
            '  "primary_cta": "string",\n'
            '  "claims": [\n'
            '    {\n'
            '      "statement": "string",\n'
            '      "category": "ON_PAGE_SEO | COMPETITIVE | UX_CONVERSION | TECHNICAL_SEO",\n'
            '      "severity": "CRITICAL | HIGH | MEDIUM | LOW",\n'
            '      "confidence": 0.90,\n'
            '      "impact": 7,\n'
            '      "effort": 4,\n'
            '      "evidence_refs": ["ev_001"],\n'
            '      "recommendation": "string"\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        result = await self.model_router.generate_structured(
            capability="semantic_extraction",
            agent_role="Lead Semantic Web Knowledge Extractor & Entity Graph Ontologist",
            task_contract=contract,
            evidence_list=evidence_list,
            rubric=(
                "1. STRICT DOM ATTRIBUTION: Zero hallucination of company names or features. Capture verbatim branding and text.\n"
                "2. EVIDENCE SELECTOR PROVENANCE: Every claim must cite verified evidence IDs from the evidence pack with observable DOM selectors.\n"
                "3. ACCURATE BUSINESS TAXONOMY: Correctly distinguish self-serve SaaS, sales-led enterprise software, agency services, and ecommerce.\n"
                "4. EXHAUSTIVE CTA CAPTURE: Extract actual button text (e.g. 'Book a Demo', 'Start Free Trial') rather than generic descriptions."
            ),
            output_schema_desc=schema_desc,
            additional_context=f"Page Topology:\n{pages_summary}"
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

        # Register Extracted Claims
        for cl in result.get("claims", []):
            cat_str = str(cl.get("category", "ON_PAGE_SEO")).upper()
            cat = Category[cat_str] if cat_str in Category.__members__ else Category.ON_PAGE_SEO
            sev_str = str(cl.get("severity", "MEDIUM")).upper()
            sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.MEDIUM

            blackboard.claim_registry.register_claim(
                agent_id=f"{self.worker_id}_{capability_id}",
                statement=cl.get("statement", "Semantic observation claim"),
                category=cat,
                severity=sev,
                confidence=float(cl.get("confidence", 0.88)),
                impact=int(cl.get("impact", 6)),
                effort=int(cl.get("effort", 4)),
                evidence_refs=cl.get("evidence_refs", []),
                recommendation=cl.get("recommendation")
            )

        return result
