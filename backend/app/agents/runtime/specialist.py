"""
Dristik Specialist Agent — one runtime class for all 35 registry agents.

Deterministic specialists inspect crawl evidence only.
LLM specialists call the model with allow_fallback=False so a missing key
or exhausted retries becomes status=unavailable, never a canned audit.
Claims without evidence_refs are dropped.
"""
from typing import Any, Dict, List, Optional

from app.agents.runtime.base import BaseAgent
from app.agents.runtime.registry import AgentDefinition, DOMAIN_CATEGORY
from app.agents.runtime.task_cards import SPECIALIST_OUTPUT_SCHEMA, task_card_for
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, VerificationStatus
from app.evidence.retriever import EvidenceRetriever
from app.inference.prompt_compiler import load_prompt


def _category_for(defn: AgentDefinition) -> Category:
    raw = DOMAIN_CATEGORY.get(defn.domain, "CONTENT")
    try:
        return Category(raw)
    except ValueError:
        return Category.CONTENT


def _severity(value: Any) -> Severity:
    text = str(value or "MEDIUM").upper()
    for item in Severity:
        if item.value == text or item.name == text:
            return item
    return Severity.MEDIUM


class SpecialistAgent(BaseAgent):
    """Parameterized specialist bound to a v3 AgentDefinition."""

    def __init__(self, definition: AgentDefinition, model_router):
        super().__init__(
            agent_id=definition.agent_id,
            capability=definition.capabilities[0] if definition.capabilities else definition.agent_id,
            model_router=model_router,
        )
        self.definition = definition
        self.is_deterministic = definition.allowed_models == ["deterministic"] or (
            "deterministic" in definition.allowed_models and "reasoning_model" not in definition.allowed_models
            and "fast_slm" not in definition.allowed_models
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=60)
        if not evidence_slice:
            evidence_slice = blackboard.evidence_store.get_all()[:60]

        if self.agent_id == "verification.adversarial.v3":
            self._falsify_unbacked_claims(blackboard)

        if self.agent_id == "verification.contradiction.v3":
            self._route_contested_claims(blackboard)

        if self._deps_unmet(blackboard):
            result = {
                "agent_id": self.agent_id,
                "status": "unavailable",
                "unavailable_reason": "dependency_missing",
                "claims": [],
            }
            self._store(blackboard, result)
            return result

        if self.is_deterministic:
            result = self._deterministic_audit(blackboard, evidence_slice)
            self._store(blackboard, result)
            return result

        if "deterministic" in (self.definition.allowed_models or []):
            det = self._deterministic_audit(blackboard, evidence_slice)
            llm_res = await self._llm_audit(blackboard, evidence_slice)
            result = self._merge(det, llm_res)
            self._store(blackboard, result)
            return result

        result = await self._llm_audit(blackboard, evidence_slice)

        self._store(blackboard, result)
        return result

    def _deps_unmet(self, blackboard: CognitiveBlackboard) -> bool:
        deps = self.definition.dependencies or []
        if not deps:
            return False
        results = (blackboard.blackboard_state.get("agent_results") or {})
        # Verification/strategy agents wait for some prior specialist output, not a hard fail
        if self.definition.domain == "VERIFICATION":
            return False
        missing = [d for d in deps if d not in results]
        # Soft: only block if ALL deps missing and deps are same-wave critical
        return len(missing) == len(deps) and len(deps) > 0 and not results

    async def _llm_audit(self, blackboard: CognitiveBlackboard, evidence_slice) -> Dict[str, Any]:
        system_extra = load_prompt("specialist_system")
        card = task_card_for(self.agent_id)
        forbidden = self.definition.forbidden_operations or []
        forbid_line = ""
        if forbidden:
            forbid_line = "Forbidden operations: " + ", ".join(forbidden) + ".\n"

        prior = self._prior_context(blackboard)
        contract = (
            f"{system_extra}\n\n"
            f"SPECIALIST: {self.definition.agent_name} ({self.agent_id})\n"
            f"TASK: {self.definition.description}\n"
            f"{card}\n"
            f"{forbid_line}"
            f"{prior}"
        )

        # Determine model tier and token budget.
        # When running under Groq (8,000 TPM limit), route routine specialists to fast_slm and budget tokens strictly.
        # Non-Groq providers (Anthropic, Gemini, OpenRouter) retain full reasoning models and token budgets.
        active_provider = getattr(getattr(self.model_router, "client", None), "provider", "")
        if not active_provider:
            from app.core.config import settings
            active_provider = settings.get_active_provider()
        is_groq = (active_provider or "").lower() == "groq"

        models = self.definition.allowed_models or []
        if is_groq:
            # Under Groq, only deep reasoning/critic/synthesis capabilities use reasoning_model
            if self.capability in ("synthesizer", "geo_analysis", "ai_search_simulation", "critic", "cross_analyst") and "reasoning_model" in models:
                tier = "reasoning_model"
            elif "fast_slm" in models:
                tier = "fast_slm"
            elif "judge_model" in models:
                tier = "judge_model"
            else:
                tier = "fast_slm"
            token_budget = min(int(self.definition.token_budget or 3000), 1000)
        else:
            if "judge_model" in models:
                tier = "judge_model"
            elif "reasoning_model" in models:
                tier = "reasoning_model"
            elif "fast_slm" in models:
                tier = "fast_slm"
            else:
                tier = "fast_slm"
            token_budget = int(self.definition.token_budget or 3000)

        max_claims = int(getattr(self.definition, "max_claims", 0) or 8)
        raw = await self.model_router.generate_structured(
            capability=self.capability,
            agent_role=self.definition.agent_name,
            task_contract=contract,
            evidence_list=evidence_slice,
            output_schema_desc=SPECIALIST_OUTPUT_SCHEMA,
            site_facts=getattr(blackboard, "site_facts", {}) or {},
            task_card=card,
            max_claims=max_claims,
            allow_fallback=False,
            model_tier=tier,
            max_tokens=token_budget,
            timeout_sec=int(self.definition.timeout_sec or 60),
        )
        return self._ingest_llm(blackboard, raw, evidence_slice)

    def _ingest_llm(self, blackboard: CognitiveBlackboard, raw: Dict[str, Any], evidence_slice) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            return {"agent_id": self.agent_id, "status": "unavailable", "unavailable_reason": "invalid_llm_payload", "claims": []}

        status = str(raw.get("status") or "completed").lower()
        if status == "unavailable" or raw.get("unavailable_reason") == "no_llm_key":
            return {
                "agent_id": self.agent_id,
                "status": "unavailable",
                "unavailable_reason": raw.get("unavailable_reason") or "unavailable",
                "claims": [],
                "mode": raw.get("mode"),
            }

        valid_ids = {ev.id for ev in evidence_slice}
        valid_ids.update(ev.id for ev in blackboard.evidence_store.get_external())
        registered = []
        max_claims = int(getattr(self.definition, "max_claims", 0) or 8)
        for item in (raw.get("claims") or [])[:max_claims]:
            if not isinstance(item, dict):
                continue
            if str(item.get("evidence_status") or "").lower() == "not_in_evidence":
                continue
            refs = [r for r in (item.get("evidence_refs") or []) if r in valid_ids]
            statement = (item.get("statement") or "").strip()
            if not statement or not refs:
                continue
            claim = self.register_claim(
                blackboard=blackboard,
                statement=statement,
                category=_category_for(self.definition),
                severity=_severity(item.get("severity")),
                evidence_refs=refs,
                confidence=float(item.get("confidence") or 0.7),
                recommendation=item.get("recommendation") or "",
                impact=int(item.get("impact") or 5),
                effort=int(item.get("effort") or 3),
            )
            registered.append(claim.id)

        observations = raw.get("observations") if isinstance(raw.get("observations"), dict) else {}
        self._apply_side_effects(blackboard, observations, raw)

        return {
            "agent_id": self.agent_id,
            "status": "completed",
            "mode": raw.get("mode") or "OBSERVED",
            "claims": registered,
            "observations": observations,
        }

    def _deterministic_audit(self, blackboard: CognitiveBlackboard, evidence_slice) -> Dict[str, Any]:
        pages = blackboard.pages or []
        manifest = blackboard.crawl_manifest
        cat = _category_for(self.definition)
        claims_spec: List[Dict[str, Any]] = []
        observations: Dict[str, Any] = {"mode": "DETERMINISTIC"}
        ev_ids = [ev.id for ev in evidence_slice[:3]]

        def add(statement: str, severity: Severity, recommendation: str, refs: Optional[List[str]] = None):
            claims_spec.append({
                "statement": statement,
                "severity": severity,
                "recommendation": recommendation,
                "refs": refs or ev_ids,
            })

        aid = self.agent_id
        ch = (manifest.crawl_health if manifest else {}) or {}

        if aid == "seo.crawl.v3" and manifest:
            observations["pages_crawled"] = len(pages)
            observations["sitemap_found"] = bool(manifest.sitemap_found)
            observations["robots_txt_found"] = bool(manifest.robots_txt_found)
            if not manifest.sitemap_found:
                is_small_site = len(pages) <= 50
                add(
                    "XML sitemap was not found during crawl (Advisory: Google discovers comprehensively linked pages on small sites, but /sitemap.xml is recommended for rapid indexation)." if is_small_site else "XML sitemap was not found during crawl.",
                    Severity.LOW if is_small_site else Severity.MEDIUM,
                    "Publish /sitemap.xml and reference it in robots.txt as an indexing best practice."
                )
            if not manifest.robots_txt_found:
                add("robots.txt was not found at the domain root.", Severity.MEDIUM, "Add a robots.txt with crawler policy and sitemap reference.")
            http_errs = [p.url for p in pages if getattr(p, "status_code", 200) >= 400]
            observations["http_errors_count"] = len(http_errs)
            if http_errs:
                add(f"{len(http_errs)} crawled URL(s) returned HTTP 4xx/5xx status error.", Severity.HIGH, "Fix broken routing or configure 301 redirects for error URLs.")

        elif aid == "seo.indexability.v3":
            missing = [p.url for p in pages if not p.canonical_url]
            observations["pages_missing_canonical"] = len(missing)
            if missing:
                add(
                    f"{len(missing)} crawled page(s) have no rel=canonical tag.",
                    Severity.MEDIUM,
                    "Add a self-referential canonical on each indexable URL.",
                )
            mismatches = [p.url for p in pages if p.canonical_url and p.canonical_url.rstrip("/") != p.url.rstrip("/")]
            observations["canonical_mismatches"] = len(mismatches)
            if mismatches:
                add(
                    f"{len(mismatches)} page(s) have canonical tag mismatch pointing away from current URL.",
                    Severity.HIGH,
                    "Ensure canonical tags point to the authoritative self-referential URL unless intentionally deduplicating.",
                )
            noindex_pages = [p.url for p in pages if p.robots_meta and "noindex" in str(p.robots_meta).lower()]
            observations["noindex_pages_count"] = len(noindex_pages)
            if noindex_pages:
                add(
                    f"{len(noindex_pages)} crawled page(s) declare noindex in robots meta directives.",
                    Severity.HIGH,
                    "Remove noindex from indexable production pages to permit search engine indexing.",
                )

        elif aid == "seo.html.v3":
            missing_h1 = [p.url for p in pages if not p.h1]
            observations["pages_missing_h1"] = len(missing_h1)
            if missing_h1:
                add(f"{len(missing_h1)} page(s) are missing an H1.", Severity.HIGH, "Add one H1 that states the page offer.")
            multi_h1 = [p.url for p in pages if p.h1 and len(p.h1) > 1]
            observations["pages_multiple_h1"] = len(multi_h1)
            if multi_h1:
                add(f"{len(multi_h1)} page(s) contain multiple H1 heading tags.", Severity.MEDIUM, "Consolidate heading tags to a single primary H1 per page.")
            missing_title = [p.url for p in pages if not p.title or not p.title.strip()]
            observations["pages_missing_title"] = len(missing_title)
            if missing_title:
                add(f"{len(missing_title)} page(s) are missing a title tag.", Severity.HIGH, "Add a unique, keyword-aligned title tag (50-60 characters) to each page.")
            title_suboptimal = [p.url for p in pages if p.title and (len(p.title.strip()) < 35 or len(p.title.strip()) > 65)]
            observations["pages_title_suboptimal"] = len(title_suboptimal)
            if title_suboptimal:
                add(f"{len(title_suboptimal)} page(s) have title tags outside optimal length (35-65 characters).", Severity.MEDIUM, "Optimize title tags to 50-60 characters to avoid SERP truncation.")
            missing_meta = [p.url for p in pages if not p.meta_description or not p.meta_description.strip()]
            observations["pages_missing_meta"] = len(missing_meta)
            if missing_meta:
                add(f"{len(missing_meta)} page(s) are missing a meta description.", Severity.HIGH, "Add an actionable meta description (140-160 characters) with a clear value proposition.")
            meta_suboptimal = [p.url for p in pages if p.meta_description and (len(p.meta_description.strip()) < 70 or len(p.meta_description.strip()) > 160)]
            observations["pages_meta_suboptimal"] = len(meta_suboptimal)
            if meta_suboptimal:
                add(f"{len(meta_suboptimal)} page(s) have meta descriptions outside recommended length (70-160 characters).", Severity.LOW, "Tune meta descriptions to 140-160 characters for complete SERP snippet display.")
            heading_skips = [p.url for p in pages if p.h1 and not p.h2 and p.h3]
            observations["pages_heading_skips"] = len(heading_skips)
            if heading_skips:
                add(f"{len(heading_skips)} page(s) have non-hierarchical heading skips (H1 to H3 without H2).", Severity.LOW, "Maintain logical H1 -> H2 -> H3 heading hierarchy for crawler parsing and accessibility.")

        elif aid == "seo.internal_links.v3":
            broken = int(ch.get("broken_links_count") or 0)
            observations["broken_links_count"] = broken
            if broken:
                add(f"Crawler recorded {broken} broken internal link(s).", Severity.HIGH, "Fix or remove broken internal hrefs.")

        elif aid == "seo.performance.v3":
            avg_ttfb = float(ch.get("avg_ttfb_ms") or 0.0)
            observations["avg_ttfb_ms"] = avg_ttfb
            if avg_ttfb > 800:
                add(
                    f"Measured average TTFB is {avg_ttfb:.0f} ms.",
                    Severity.HIGH if avg_ttfb > 1500 else Severity.MEDIUM,
                    "Improve origin TTFB (caching, less blocking work). LCP/CLS were not measured.",
                )

        elif aid == "seo.security.v3":
            url = blackboard.website_url or (manifest.base_url if manifest else "")
            is_https = url.startswith("https://")
            observations["https"] = is_https
            if not is_https:
                add("Crawl URL is not HTTPS.", Severity.CRITICAL, "Serve the site on HTTPS and redirect HTTP.")
            all_headers = {}
            for p in pages:
                for k, v in (getattr(p, "response_headers", None) or {}).items():
                    all_headers[k.lower()] = v
            if not all_headers and manifest and getattr(manifest, "headers", None):
                all_headers = {k.lower(): v for k, v in manifest.headers.items()}
            observations["headers_audited"] = list(all_headers.keys())
            if all_headers:
                if "strict-transport-security" not in all_headers:
                    add("Strict-Transport-Security (HSTS) header is missing.", Severity.HIGH, "Configure HSTS with max-age=31536000 and includeSubDomains.")
                if "content-security-policy" not in all_headers:
                    add("Content-Security-Policy (CSP) header is missing.", Severity.HIGH, "Implement a Content-Security-Policy header to prevent cross-site scripting.")
                if "x-frame-options" not in all_headers:
                    add("X-Frame-Options header is missing (clickjacking protection).", Severity.MEDIUM, "Set X-Frame-Options: SAMEORIGIN or DENY to prevent clickjacking.")
                if "x-content-type-options" not in all_headers:
                    add("X-Content-Type-Options header is missing (MIME-sniffing risk).", Severity.LOW, "Set X-Content-Type-Options: nosniff to protect against MIME type confusion.")

        elif aid == "seo.assets.v3":
            missing_alt = sum(getattr(p, "images_without_alt", 0) or 0 for p in pages)
            observations["images_without_alt"] = missing_alt
            if missing_alt:
                add(f"{missing_alt} image(s) are missing alt text.", Severity.MEDIUM, "Add descriptive alt text on content images.")

        elif aid == "schema.validation.v3":
            without = [p.url for p in pages if not p.schema_types]
            types = sorted({t for p in pages for t in (p.schema_types or [])})
            observations["schema_types"] = types
            if pages and len(without) == len(pages):
                add("No JSON-LD or microdata schema types were parsed on crawled pages.", Severity.HIGH, "Add Organization and WebSite JSON-LD if those entities exist.")
            elif not any(t.lower() in ("organization", "corporation", "localbusiness") for t in types):
                add("Missing Organization or LocalBusiness structured data schema.", Severity.MEDIUM, "Implement Organization JSON-LD with official brand name, logo, and sameAs social profiles.")

        elif aid == "content.cannibalization.v3":
            dup = int(ch.get("duplicate_titles_count") or 0)
            observations["duplicate_titles_count"] = dup
            if len(pages) < 2:
                return {
                    "agent_id": self.agent_id,
                    "status": "unavailable",
                    "unavailable_reason": "need_two_pages",
                    "claims": [],
                    "observations": observations,
                }
            if dup:
                add(f"{dup} duplicate title collision(s) across crawled pages.", Severity.HIGH, "Give each URL a distinct title.")

        elif aid == "cro.conversion.v3":
            no_cta = [p.url for p in pages if not getattr(p, "ctas", None)]
            observations["pages_without_cta"] = len(no_cta)
            if no_cta and len(no_cta) == len(pages):
                add(f"No clear Call-To-Action (CTA) elements detected on crawled pages.", Severity.HIGH, "Add prominent, value-driven CTA buttons in hero sections.")

        elif aid == "ux.experience.v3":
            missing_vp = [p.url for p in pages if not getattr(p, "viewport", None)]
            observations["pages_missing_viewport"] = len(missing_vp)
            if missing_vp:
                add(f"{len(missing_vp)} page(s) lack a viewport meta tag.", Severity.HIGH, "Add width=device-width viewport meta.")

        registered = []
        for spec in claims_spec:
            refs = [r for r in (spec["refs"] or []) if r]
            if not refs:
                continue
            claim = self.register_claim(
                blackboard=blackboard,
                statement=spec["statement"],
                category=cat,
                severity=spec["severity"],
                evidence_refs=refs,
                confidence=0.95,
                recommendation=spec["recommendation"],
            )
            registered.append(claim.id)

        return {
            "agent_id": self.agent_id,
            "status": "completed",
            "mode": "DETERMINISTIC",
            "claims": registered,
            "observations": observations,
        }

    def _merge(self, det: Dict[str, Any], llm: Dict[str, Any]) -> Dict[str, Any]:
        claims = list(det.get("claims") or [])
        for cid in llm.get("claims") or []:
            if cid not in claims:
                claims.append(cid)
        obs = dict(det.get("observations") or {})
        obs.update(llm.get("observations") or {})
        status = "completed" if claims or llm.get("status") == "completed" else llm.get("status") or det.get("status")
        return {
            "agent_id": self.agent_id,
            "status": status,
            "mode": llm.get("mode") or det.get("mode"),
            "claims": claims,
            "observations": obs,
            "unavailable_reason": llm.get("unavailable_reason") if status == "unavailable" and not claims else None,
        }

    def _prior_context(self, blackboard: CognitiveBlackboard) -> str:
        results = blackboard.blackboard_state.get("agent_results") or {}
        deps = self.definition.dependencies or []
        lines = []
        if self.agent_id == "strategy.executive.v3":
            from app.cognition.finding_rubric import executive_eligible_claims
            eligible = executive_eligible_claims(blackboard.claim_registry.get_all())
            held = [
                c.id for c in blackboard.claim_registry.get_all()
                if c.held_from_executive and not c.adversarial_reviewed
            ]
            lines.append(
                "Use ONLY executive-eligible claims (exclude GUESSING+CRITICAL until "
                "verification.adversarial.v3 has reviewed them)."
            )
            lines.append(f"Eligible claims: {len(eligible)}. Held for adversarial: {held or 'none'}.")
        if not deps and not lines:
            return ""
        lines.append("Prior specialist outputs (do not treat as new evidence):")
        for dep in deps:
            payload = results.get(dep) or {}
            lines.append(f"- {dep}: status={payload.get('status')} claims={len(payload.get('claims') or [])}")
        return "\n".join(lines) + "\n"

    def _apply_side_effects(self, blackboard: CognitiveBlackboard, observations: Dict[str, Any], raw: Dict[str, Any]) -> None:
        if self.agent_id == "strategy.executive.v3":
            story = observations.get("story_summary") or raw.get("story_summary")
            if story and not blackboard.executive_narrative.get("story_summary"):
                blackboard.executive_narrative = {
                    **blackboard.executive_narrative,
                    "story_summary": story,
                    "what_is_holding_it_back": observations.get("blockers") or [],
                    "consultant_advice_what_to_ignore": observations.get("what_to_ignore") or "",
                }
        if self.agent_id == "business.discovery.v3":
            name = observations.get("business_name")
            if name and blackboard.business_profile and blackboard.business_profile.business_name in (
                "Unknown Business", "Unknown", "Identified Platform", ""
            ):
                blackboard.business_profile.business_name = str(name)

    def _route_contested_claims(self, blackboard: CognitiveBlackboard) -> None:
        """Arbitrate only by recording DOM vs ext contests. Never pick a winner."""
        from app.domain.enums import SourceIntegrityLabel, VerificationStatus
        from app.cognition.contradiction import ContradictionDetector

        detector = ContradictionDetector()
        routed = detector.detect_contradictions(blackboard.claim_registry.get_all())
        existing = {(c.claim_a_id, c.claim_b_id, c.resolution) for c in blackboard.claim_registry.get_contradictions()}
        for contra in routed:
            key = (contra.claim_a_id, contra.claim_b_id, contra.resolution)
            if key in existing:
                continue
            if contra.winner_claim_id:
                continue
            blackboard.claim_registry.register_contradiction(
                claim_a_id=contra.claim_a_id,
                claim_b_id=contra.claim_b_id,
                description=contra.description,
                resolution=contra.resolution,
                winner_claim_id=None,
                routed_to=contra.routed_to,
            )
            existing.add(key)
        blackboard.contradictions = blackboard.claim_registry.get_contradictions()
        for claim in blackboard.claim_registry.get_all():
            if claim.source_integrity_label == SourceIntegrityLabel.CONTESTED:
                claim.verification_status = VerificationStatus.CONTESTED
                claim.routed_to = "verification.contradiction.v3"

    def _falsify_unbacked_claims(self, blackboard: CognitiveBlackboard) -> None:
        """Drop confidence on claims whose evidence IDs are missing. Does not invent replacements."""
        store = blackboard.evidence_store
        for claim in blackboard.claim_registry.get_all():
            valid = [ref for ref in (claim.evidence_refs or []) if store.get(ref)]
            if not valid:
                claim.confidence = min(float(claim.confidence or 0), 0.40)
                claim.verification_status = VerificationStatus.INSUFFICIENT_EVIDENCE
                claim.verification_notes = "Adversarial specialist: no surviving evidence_refs."
        from app.domain.enums import Materiality, RubricConfidence
        from app.cognition.finding_rubric import apply_rubric_to_claim, ADVERSARIAL_AGENT_ID
        for claim in blackboard.claim_registry.get_all():
            apply_rubric_to_claim(claim, store)
            if (
                claim.confidence_rubric == RubricConfidence.GUESSING
                and claim.materiality == Materiality.CRITICAL
            ):
                claim.adversarial_reviewed = True
                claim.held_from_executive = False
                claim.routed_to = ADVERSARIAL_AGENT_ID
                note = "Adversarial review of GUESSING+CRITICAL completed; still GUESSING — not CERTAIN/LIKELY."
                existing = claim.verification_notes or ""
                if note not in existing:
                    claim.verification_notes = f"{existing} | {note}".strip(" |")

    def _store(self, blackboard: CognitiveBlackboard, result: Dict[str, Any]) -> None:
        store = blackboard.blackboard_state.setdefault("agent_results", {})
        store[self.agent_id] = result
        blackboard.log_step(
            f"Specialist {self.definition.agent_name}",
            self.agent_id,
            {"status": result.get("status"), "claims": len(result.get("claims") or [])},
        )
