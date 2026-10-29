"""
Dristik AI Generative Engine Optimization (GEO) Agent (70B-Hardened)
Analyzes AI answer engine extractability (ChatGPT Search, Perplexity, Google AI Overviews, Claude, Gemini).
Relies on Wave-0 deterministic schema inventory and computes scores deterministically in code.
"""
import json
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity
from app.evidence.retriever import EvidenceRetriever
from app.inference.prompt_compiler import load_prompt
from app.inference.schemas import GeoAuditOutput, legacy_adapt

TARGET_SCHEMAS = {"Organization", "WebSite", "SoftwareApplication", "Product", "FAQPage"}

class GeoAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_geo", capability="geo_analysis", model_router=model_router)

    def _compute_schema_completeness(self, detected: List[str]) -> int:
        det_set = set(detected)
        # SoftwareApplication or Product counts as the product schema slot
        matched = 0
        if "Organization" in det_set:
            matched += 1
        if "WebSite" in det_set:
            matched += 1
        if "SoftwareApplication" in det_set or "Product" in det_set:
            matched += 1
        if "FAQPage" in det_set:
            matched += 1
        return int((matched / 4.0) * 100)

    def _compute_direct_answer_density(self, blackboard: CognitiveBlackboard) -> int:
        """Computes the percentage of H2/H3 text blocks with 40-60 words of declarative text."""
        pages = blackboard.pages or []
        if not pages:
            return 0
        valid_blocks = 0
        total_headers = 0
        for p in pages[:4]:
            headers = (p.h2 or []) + (p.h3 or [])
            total_headers += len(headers)
            body = p.body_text or ""
            words = body.split()
            # If body has reasonable length per header
            if len(words) >= 40 * max(1, len(headers)):
                valid_blocks += len(headers)

        if total_headers == 0:
            return 0
        ratio = min(1.0, valid_blocks / max(1, total_headers))
        return int(ratio * 100)

    def _clean_jsonld_patch(self, patch: Dict[str, Any], site_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitizes JSON-LD patch:
        - If logo URL unknown or unobserved, omit logo.
        - If social URLs unknown, sameAs: [].
        - No unobserved external profile URLs in patch.
        """
        if not isinstance(patch, dict):
            return {"@context": "https://schema.org", "@graph": []}

        observed_sameas = set(site_facts.get("sameas_urls", []))
        entities = patch.get("@graph", [patch]) if isinstance(patch.get("@graph"), list) else [patch]

        for ent in entities:
            if not isinstance(ent, dict):
                continue
            # Check sameAs
            if "sameAs" in ent:
                curr_sameas = ent["sameAs"]
                if isinstance(curr_sameas, list):
                    ent["sameAs"] = [s for s in curr_sameas if s in observed_sameas]
                elif isinstance(curr_sameas, str):
                    ent["sameAs"] = [curr_sameas] if curr_sameas in observed_sameas else []
                else:
                    ent["sameAs"] = []
            # Check logo
            if "logo" in ent:
                logo_val = str(ent.get("logo", ""))
                if not logo_val.startswith("http") or "example.com" in logo_val:
                    ent.pop("logo", None)

        return patch

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=25)
        site_facts = getattr(blackboard, "site_facts", {}) or {}

        geo_prompt = load_prompt("geo")
        geo_card = (
            "Audit extractability for AI answer engines using provided schema inventory and copy blocks.\n"
            "Treat <site_facts>.schemas_detected as ground truth.\n"
            "Do not invent sameAs profile URLs.\n"
            "JSON-LD patch may only use names, URLs, and logos present in evidence or site_facts.\n"
            "If a recommended sameAs target is not observed, put it in sameas_recommended as a search hint, never inside the patch as a live URL unless observed.\n"
            "Max 3 claims."
        )

        detected_schemas = site_facts.get("schemas_detected", [])
        code_schema_completeness = self._compute_schema_completeness(detected_schemas)
        code_density_score = self._compute_direct_answer_density(blackboard)

        result = await self.model_router.generate_structured(
            capability=self.capability,
            agent_role="Principal AI Answer Engine & Semantic Knowledge Graph Architect",
            task_contract=geo_prompt or geo_card,
            evidence_list=evidence_slice,
            output_schema_desc=json.dumps(GeoAuditOutput.model_json_schema(), indent=2),
            site_facts=site_facts,
            task_card=geo_card,
            max_claims=3
        )

        adapted = legacy_adapt("geo", result)
        adapted["schema_completeness"] = code_schema_completeness
        adapted["direct_answer_density_score"] = code_density_score

        # Missing schemas calculation in code
        missing = [s for s in ["Organization", "WebSite", "SoftwareApplication", "FAQPage"] if s not in detected_schemas]
        adapted["schemas_detected"] = detected_schemas
        adapted["schemas_missing"] = missing

        # Clean JSON-LD patch
        if adapted.get("production_jsonld_patch"):
            adapted["production_jsonld_patch"] = self._clean_jsonld_patch(adapted["production_jsonld_patch"], site_facts)

        # Store GEO patches and diagnostics in blackboard
        if adapted.get("production_jsonld_patch"):
            blackboard.blackboard_state["production_jsonld_patch"] = adapted["production_jsonld_patch"]
        if adapted.get("sameas_recommended"):
            blackboard.blackboard_state["sameas_recommended"] = adapted["sameas_recommended"]
        if adapted.get("schemas_missing"):
            blackboard.blackboard_state["schemas_missing"] = adapted["schemas_missing"]

        # Register claims (max 3)
        for c in adapted.get("claims", [])[:3]:
            sev_str = str(c.get("severity", "MEDIUM")).upper()
            sev_enum = Severity.MEDIUM
            for s in Severity:
                if s.value == sev_str:
                    sev_enum = s
                    break

            conf_val = c.get("confidence")
            confidence = float(conf_val) if conf_val is not None else (0.80 if c.get("evidence_refs") else 0.50)

            self.register_claim(
                blackboard=blackboard,
                statement=c.get("statement", "Entity clarity observation"),
                category=Category.GEO,
                severity=sev_enum,
                evidence_refs=c.get("evidence_refs") or [],
                confidence=confidence,
                recommendation=c.get("recommendation", "Deploy structured Schema.org JSON-LD definitions."),
                impact=c.get("impact", 8),
                effort=c.get("effort", 3)
            )

        blackboard.log_step("GEO & Entity Clarity Analyzed (70B Hardened)", self.agent_id, {
            "entity_clarity_score": adapted.get("entity_clarity_score"),
            "schema_completeness": code_schema_completeness,
            "direct_answer_density": code_density_score,
            "claims_count": len(adapted.get("claims", []))
        })
        return adapted
