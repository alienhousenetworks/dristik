"""
Dristik AI Model Router & Multi-Provider Inference Gateway
Provides capability-based routing, 70B-hardened prompt compilation, two-pass reason-then-json execution,
JSON auto-repair, adaptive backoff, and number hallucination sanitization.
"""
import asyncio
import json
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, ValidationError

from app.core.config import (
    settings,
    ANTHROPIC_DEFAULT_FAST,
    ANTHROPIC_FALLBACK_MODEL,
    GROQ_DEFAULT_FAST,
    GROQ_DEFAULT_REASONING,
)
from app.evidence.models import Evidence
from app.core.inference.budget_manager import BudgetManager
from app.core.inference.llm_client import (
    LLMClient,
    RateLimitException,
    _looks_like_json_document,
    use_tenant_context,
)
from app.core.inference.prompt_compiler import PromptCompiler, load_prompt
from app.core.inference.json_repair import repair_and_parse_json
from app.core.inference.telemetry import TelemetryTracker
from app.core.inference.fallback import DeterministicFallbackEngine
from app.core.inference.schemas.shared import strip_ungrounded_numbers

logger = logging.getLogger(__name__)

_ACTIVE_PROVIDER_OVERRIDE: ContextVar[tuple[str, str] | None] = ContextVar("dristik_provider_override", default=None)


@contextmanager
def use_provider_override(provider_id: str, org_id: str):
    """Route ModelRouter calls in the current async task through one tenant-owned provider."""
    token = _ACTIVE_PROVIDER_OVERRIDE.set((provider_id, org_id))
    with use_tenant_context(org_id):
        try:
            yield
        finally:
            _ACTIVE_PROVIDER_OVERRIDE.reset(token)

class ModelRouter:
    def __init__(
        self,
        telemetry_tracker: Optional[TelemetryTracker] = None,
        max_budget_usd: Optional[float] = None,
        max_model_calls: Optional[int] = None,
    ):
        self.client = LLMClient()
        self.together_client = self.client  # backward compatibility
        self.prompt_compiler = PromptCompiler()
        self.telemetry = telemetry_tracker or TelemetryTracker()
        self.fallback_engine = DeterministicFallbackEngine()
        self._explicit_budget_override = (max_budget_usd is not None) or (max_model_calls is not None)
        resolved_budget = (
            float(getattr(settings, "ANALYSIS_MAX_COST_USD", 2.50))
            if max_budget_usd is None
            else float(max_budget_usd)
        )
        self.budget_manager = BudgetManager(max_budget_usd=resolved_budget)
        self.max_model_calls = (
            int(getattr(settings, "ANALYSIS_MAX_MODEL_CALLS", 150))
            if max_model_calls is None
            else int(max_model_calls)
        )

    def _is_budget_exhausted(self) -> Optional[str]:
        """Enforce hard per-audit USD and call-count budgets before any LLM dispatch."""
        if not self._explicit_budget_override and not getattr(settings, "ENFORCE_HARD_BUDGET_CAP", True):
            return None
        td = getattr(self.telemetry, "telemetry", None)
        if td is None:
            return None
        if self.max_model_calls > 0 and (td.model_calls_count or 0) >= self.max_model_calls:
            return f"max_model_calls_reached ({td.model_calls_count}/{self.max_model_calls})"
        if self.budget_manager.max_budget_usd > 0:
            status = self.budget_manager.check_budget(td)
            if status.is_exceeded:
                return f"max_cost_usd_reached (${status.current_spent_usd:.4f}/${status.max_budget_usd:.4f})"
        return None

    async def _generate_chat_completion(self, **kwargs: Any) -> Dict[str, Any]:
        """Use the explicitly selected tenant provider for this run, otherwise the platform client."""
        override = _ACTIVE_PROVIDER_OVERRIDE.get()
        if override is None:
            return await self.client.generate_chat_completion(**kwargs)

        provider_id, org_id = override
        from app.api.routes.integrations import provider_adapters

        with provider_adapters._db() as conn:
            row = conn.execute(
                "SELECT provider,model,encrypted_secret,status FROM uc_provider_credentials WHERE id=? AND org_id=?",
                (provider_id, org_id),
            ).fetchone()
        if row is None or row["status"] != "healthy":
            raise RuntimeError("Selected model provider is not healthy or is unavailable for this organization.")
        try:
            api_key = provider_adapters._cipher().decrypt(row["encrypted_secret"].encode()).decode()
        except Exception as exc:
            raise RuntimeError("Selected model provider credentials could not be decrypted.") from exc

        started = time.perf_counter()
        response = await provider_adapters._invoke(
            row["provider"], row["model"], api_key,
            str(kwargs.get("user_prompt") or ""),
            kwargs.get("system_prompt"),
            int(kwargs.get("max_tokens") or 1200),
            float(kwargs.get("temperature") if kwargs.get("temperature") is not None else 0.1),
        )
        usage = response.get("usage") or {}
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", usage.get("promptTokenCount", 0)))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens", usage.get("candidatesTokenCount", 0)))
        return {
            "content": response.get("text", ""),
            "provider": row["provider"],
            "model": row["model"],
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "latency_ms": (time.perf_counter() - started) * 1000,
            "stop_reason": None,
        }

    def set_active_stage(self, stage: str, display_name: Optional[str] = None) -> None:
        if hasattr(self.telemetry, "set_active_stage"):
            self.telemetry.set_active_stage(stage, display_name)

    def set_active_sub_stage(self, sub_step: str, display_name: Optional[str] = None) -> None:
        if hasattr(self.telemetry, "set_active_sub_stage"):
            self.telemetry.set_active_sub_stage(sub_step, display_name)

    def _record_llm_call(
        self,
        *,
        response: Dict[str, Any],
        capability: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        agent_id: str,
        is_reasoning: bool = False,
    ) -> None:
        from app.evidence.provenance import sha256_text

        is_cache_hit = bool(response.get("cache_hit") or response.get("cached"))
        self.telemetry.record_call(
            input_tokens=0 if is_cache_hit else int(response.get("input_tokens") or 0),
            output_tokens=0 if is_cache_hit else int(response.get("output_tokens") or 0),
            latency_ms=0.0 if is_cache_hit else float(response.get("latency_ms") or 0),
            capability=capability,
            is_reasoning=is_reasoning,
            model=response.get("model") or model,
            provider=response.get("provider") or getattr(self.client, "provider", "unknown"),
            prompt_sha256=sha256_text(system_prompt + "\n" + user_prompt),
            prompt_template_sha256=sha256_text(system_prompt),
            agent_id=agent_id,
            provider_cost_usd=0.0 if is_cache_hit else response.get("provider_cost_usd"),
        )

    # Capabilities routed to the Frontier reasoning model under tiered_frontier mode.
    FRONTIER_CAPABILITIES = frozenset({
        "business_discovery",
        "business_intelligence",
        "intent_journey",
        "category_product",
        "business_model",
        "semantic_strategist",
        "seo_verification",
        "geo_analysis",
        "aeo_question_synthesis",
        "aeo_analysis",
        "cro_analysis",
        "ux_conversion",
        "content_analysis",
        "content_intelligence",
        "remediation_synthesis",
        "roadmap_synthesis",
        "report_narrative",
        "synthesizer",
        "critic",
        "ai_search_simulation",
        "cross_analyst",
    })

    def apply_page_budget(self, pages_count: int, depth_mode: Optional[str] = None):
        """Scale audit budget and call limits dynamically from crawled page count (~₹20–₹30/page)."""
        plan = BudgetManager.compute_audit_budget(pages_count, depth_mode=depth_mode)
        if not self._explicit_budget_override:
            self.budget_manager.max_budget_usd = plan.max_budget_usd
            self.max_model_calls = plan.max_model_calls
        return plan

    def _select_model(
        self,
        capability: str,
        model_tier: Optional[str] = None,
        provider_override: Optional[str] = None,
    ) -> str:
        """
        Capability-based Frontier routing:
        - AI_DEPTH_MODE=frontier_all routes all calls to model_reasoning.
        - AI_DEPTH_MODE=tiered_frontier routes strategic capabilities and reasoning/judge
          tiers to model_reasoning, keeping fast_slm for high-volume map/batch fanout.
        """
        creds = settings.get_llm_credentials(provider_override=provider_override)
        depth_mode = (getattr(settings, "AI_DEPTH_MODE", "tiered_frontier") or "tiered_frontier").strip().lower()
        tier = (model_tier or "").strip()
        if depth_mode == "frontier_all":
            return creds["model_reasoning"]
        if tier in ("reasoning_model", "judge_model", "reasoning", "frontier"):
            return creds["model_reasoning"]
        if tier in ("fast_slm", "fast"):
            return creds["model_fast"]
        if capability in self.FRONTIER_CAPABILITIES:
            return creds["model_reasoning"]
        return creds["model_fast"]

    def _next_model_after_missing(
        self, current_model: str, fast_model: str, tried_missing: set
    ) -> Optional[str]:
        """Pick a different live model after a 404 / model_not_found. None if none remain."""
        tried_missing.add(current_model)
        provider = getattr(self.client, "provider", "")
        if provider == "groq":
            candidates = [GROQ_DEFAULT_FAST, GROQ_DEFAULT_REASONING, fast_model]
        elif provider in ("anthropic", "claude"):
            candidates = [ANTHROPIC_DEFAULT_FAST, ANTHROPIC_FALLBACK_MODEL, fast_model]
        else:
            candidates = [fast_model]
        for candidate in candidates:
            if candidate and candidate not in tried_missing:
                return candidate
        return None

    async def generate_prose(
        self,
        capability: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 3000
    ) -> str:
        """
        Generates free prose text (for reason passes) without forcing json_object response_format.
        """
        budget_reason = self._is_budget_exhausted()
        if budget_reason:
            logger.warning("[ModelRouter][%s] Skipping generate_prose due to budget cap: %s", capability, budget_reason)
            return ""

        model = self._select_model(capability)
        creds = settings.get_llm_credentials()
        fast_model = creds.get("model_fast") or GROQ_DEFAULT_FAST

        current_model = model
        last_error = None
        max_attempts = 2
        tried_missing: set = set()

        for attempt in range(max_attempts):
            try:
                if current_model in tried_missing:
                    break

                response = await self._generate_chat_completion(
                    model=current_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=None
                )
                self._record_llm_call(
                    response=response,
                    capability=capability,
                    model=current_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    agent_id=capability,
                    is_reasoning=True,
                )
                return response.get("content", "")
            except RateLimitException as rle:
                last_error = rle
                logger.warning("[ModelRouter][%s] Rate limit exhausted from LLMClient: %s", capability, rle)
                break
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                missing = (_ACTIVE_PROVIDER_OVERRIDE.get() is None) and ("does not exist" in msg or "http 404" in msg or "model_not_found" in msg)
                if missing:
                    nxt = self._next_model_after_missing(current_model, fast_model, tried_missing)
                    if not nxt:
                        logger.warning("Model %s missing (%s); no distinct fallback remains", current_model, e)
                        break
                    logger.warning("Model %s missing (%s); retrying with %s", current_model, e, nxt)
                    current_model = nxt
                    continue
                logger.warning("[ModelRouter][%s] generate_prose failed: %s", capability, e)
                break

        logger.warning("generate_prose failed: %s", last_error)
        return ""

    async def generate_structured(
        self,
        capability: str,
        agent_role: str,
        task_contract: str,
        evidence_list: Optional[List[Evidence]] = None,
        rubric: str = "",
        output_schema_desc: str = "",
        additional_context: Optional[str] = None,
        site_facts: Optional[Dict[str, Any]] = None,
        task_card: Optional[str] = None,
        max_claims: int = 8,
        allow_fallback: bool = False,
        model_tier: Optional[str] = None,
        max_tokens: Optional[int] = None,
        timeout_sec: Optional[int] = None,
        evidence_max_tokens: Optional[int] = None,
        provider_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compiles prompt with 70B envelope, invokes active LLM provider, parses structured JSON,
        and sanitizes ungrounded numbers.
        When allow_fallback is False, missing keys or exhausted retries return {} instead of
        a canned fallback audit (specialist agents must not invent results).
        """
        evidence_list = evidence_list if evidence_list is not None else []
        budget_reason = self._is_budget_exhausted()
        if budget_reason:
            logger.warning("[ModelRouter][%s] Skipping generate_structured due to budget cap: %s", capability, budget_reason)
            return {
                "status": "budget_exceeded",
                "unavailable_reason": budget_reason,
                "claims": [],
            }
        if not settings.has_active_llm_key and _ACTIVE_PROVIDER_OVERRIDE.get() is None:
            if not allow_fallback:
                return {"status": "unavailable", "unavailable_reason": "no_llm_key", "claims": []}
            return self.fallback_engine.execute_fallback(
                capability=capability,
                evidence_list=evidence_list,
                additional_context=additional_context or ""
            )

        model = self._select_model(capability, model_tier=model_tier, provider_override=provider_override)
        creds = settings.get_llm_credentials(provider_override=provider_override)
        fast_model = creds.get("model_fast") or GROQ_DEFAULT_FAST
        tier = (model_tier or "").strip()
        is_reasoning = (model == creds.get("model_reasoning")) or tier in ("reasoning_model", "judge_model", "reasoning", "frontier")

        # Evidence token budget: 2400 cap for Groq's 8k TPM & small local models, full AI_EVIDENCE_MAX_TOKENS (12k) for Frontier cloud providers
        active_prov = (provider_override or getattr(self.client, "provider", "") or settings.get_active_provider()).lower()
        configured_ev_budget = int(getattr(settings, "AI_EVIDENCE_MAX_TOKENS", 12000) or 12000)
        default_ev_budget = min(configured_ev_budget, 2400) if active_prov in ("groq", "local", "ollama", "lmstudio", "llamacpp") else configured_ev_budget
        evidence_budget = int(evidence_max_tokens) if evidence_max_tokens is not None else default_ev_budget

        # 1. Compile structured prompt with 70B envelope
        prompts = self.prompt_compiler.compile(
            agent_role=agent_role,
            task_contract=task_contract,
            evidence_list=evidence_list,
            rubric=rubric,
            output_schema_desc=output_schema_desc,
            additional_context=additional_context,
            site_facts=site_facts,
            task_card=task_card,
            max_claims=max_claims,
            evidence_max_tokens=evidence_budget,
        )

        # 2. Call LLM API with single-pass retries handled by LLMClient, plus 1 JSON-repair attempt if needed
        current_model = model
        last_error = None
        max_attempts = 2
        tried_missing: set = set()
        user_prompt = prompts["user"]
        max_tokens = int(max_tokens or settings.LLM_MAX_TOKENS)
        if capability in ("content_intelligence", "synthesizer", "geo_analysis") and max_tokens < 4096:
            max_tokens = 4096
        call_timeout = int(timeout_sec) if timeout_sec else None

        # Evidence text for number grounding check
        ev_text = " ".join([f"{ev.text or ''} {str(ev.value or '')}" for ev in evidence_list])
        if site_facts:
            ev_text += " " + str(site_facts)

        for attempt in range(max_attempts):
            try:
                if current_model in tried_missing:
                    break

                call_kwargs = dict(
                    model=current_model,
                    system_prompt=prompts["system"],
                    user_prompt=user_prompt,
                    temperature=0.0 if "extract" in capability else settings.LLM_TEMPERATURE,
                    max_tokens=max_tokens,
                    timeout=call_timeout,
                )
                if provider_override and _ACTIVE_PROVIDER_OVERRIDE.get() is None:
                    call_kwargs["provider_override"] = provider_override
                response = await self._generate_chat_completion(**call_kwargs)

                self._record_llm_call(
                    response=response,
                    capability=capability,
                    model=current_model,
                    system_prompt=prompts["system"],
                    user_prompt=user_prompt,
                    agent_id=agent_role,
                    is_reasoning=is_reasoning,
                )

                parsed = repair_and_parse_json(response["content"])
                if parsed:
                    # Sanitize ungrounded numbers
                    sanitized = strip_ungrounded_numbers(parsed, ev_text)
                    # Assign code-minted claim IDs if claims exist
                    if isinstance(sanitized, dict) and "claims" in sanitized and isinstance(sanitized["claims"], list):
                        for idx, cl in enumerate(sanitized["claims"], start=1):
                            if isinstance(cl, dict) and not cl.get("claim_id"):
                                cl["claim_id"] = f"claim_{idx:02d}"
                    return sanitized
                else:
                    raw = response.get("content") or ""
                    stop_reason = response.get("stop_reason")
                    last_error = ValueError(
                        f"Could not parse valid JSON from {self.client.provider} response "
                        f"for capability '{capability}' (stop_reason={stop_reason}, chars={len(raw)})."
                    )
                    logger.warning("[ModelRouter][%s][%s] %s Preview: %s", capability, agent_role, last_error, raw[:300].replace("\n", " "))
                    # A thinking trace is not a truncated JSON document. Growing
                    # max_tokens only gives the trace more room and blows the timeout.
                    if (
                        stop_reason in ("max_tokens", "length")
                        and max_tokens < 8192
                        and _looks_like_json_document(raw)
                    ):
                        max_tokens = min(max_tokens * 2, 8192)
                        user_prompt = (
                            f"{prompts['user']}\n\n"
                            "CRITICAL: PREVIOUS OUTPUT WAS CUT OFF BY TOKEN LIMIT. "
                            "Be extremely concise, minimize internal reasoning/chain-of-thought, "
                            "and output ONLY the valid JSON object immediately without preamble or commentary."
                        )
                    else:
                        user_prompt = (
                            f"{prompts['user']}\n\n"
                            "PREVIOUS OUTPUT WAS NOT VALID JSON. Return a single JSON object only. "
                            "No markdown fences, no preamble, no trailing commentary."
                        )
                    continue

            except RateLimitException as rle:
                last_error = rle
                logger.warning(
                    "[ModelRouter][%s][%s] Rate limit exhausted from LLMClient: %s",
                    capability, agent_role, rle
                )
                break
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                missing = (_ACTIVE_PROVIDER_OVERRIDE.get() is None) and ("does not exist" in msg or "http 404" in msg or "model_not_found" in msg)
                if missing:
                    nxt = self._next_model_after_missing(current_model, fast_model, tried_missing)
                    if not nxt:
                        logger.warning("[ModelRouter][%s][%s] Model %s missing (%s); no distinct fallback remains", capability, agent_role, current_model, e)
                        break
                    logger.warning("[ModelRouter][%s][%s] Model %s missing (%s); retrying with %s", capability, agent_role, current_model, e, nxt)
                    current_model = nxt
                    continue
                logger.warning(
                    "[ModelRouter][%s][%s] Call failed on attempt %d: %s (%s)",
                    capability, agent_role, attempt + 1, e, type(e).__name__
                )
                break

        # 3. Exhausted retries — specialists must not receive canned audits
        if not allow_fallback:
            return {
                "status": "unavailable",
                "unavailable_reason": f"llm_exhausted:{last_error}",
                "claims": [],
            }
        fallback_res = self.fallback_engine.execute_fallback(
            capability=capability,
            evidence_list=evidence_list,
            additional_context=additional_context or ""
        )
        if fallback_res:
            return fallback_res

        raise RuntimeError(f"LLM inference ({self.client.provider}) failed for capability '{capability}': {last_error}")

    async def run_reason_then_json(
        self,
        capability: str,
        agent_role: str,
        reason_contract: str,
        schema_cls: Type[BaseModel],
        evidence_list: List[Evidence],
        site_facts: Optional[Dict[str, Any]] = None,
        additional_context: Optional[str] = None,
        task_card: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Two-pass execution helper (Section 4.3):
        Pass 1: Generate reasoning + cited evidence IDs in free text (temp 0.2, prose).
        Pass 2: Serialize into constrained JSON schema (temp 0.0).
        Validate with Pydantic with 1 retry on ValidationError.
        """
        if not settings.has_active_llm_key and _ACTIVE_PROVIDER_OVERRIDE.get() is None:
            return {
                "status": "unavailable",
                "unavailable_reason": "no_llm_key",
                "error": "Required LLM inference provider is not configured or active."
            }


        # 1. Reason Pass
        reason_prompts = self.prompt_compiler.compile(
            agent_role=agent_role,
            task_contract=f"{reason_contract}\n\nDeliver your analysis in dense, analytical prose. Cite verified evidence IDs from the evidence pack. Never output literal placeholder tokens like [ev_xxx] or [ext_xxx]. Do NOT output JSON.",
            evidence_list=evidence_list,
            site_facts=site_facts,
            task_card=task_card
        )

        analysis_prose = await self.generate_prose(
            capability=capability,
            system_prompt=reason_prompts["system"],
            user_prompt=reason_prompts["user"],
            temperature=0.2
        )

        # 2. Serialize Pass
        serializer_template = load_prompt("serializer")
        if not serializer_template:
            serializer_template = (
                "You are a JSON serializer for an audit system.\n"
                "Convert ANALYSIS into the target schema.\n"
                "Rules:\n"
                "- No new facts, names, URLs, products, customers, or numbers.\n"
                "- If ANALYSIS does not support a field, use null and evidence_status=\"not_in_evidence\".\n"
                "- evidence_refs may only contain IDs that appear in ANALYSIS or <evidence>.\n"
                "- No markdown. No preamble."
            )

        schema_json_desc = json.dumps(schema_cls.model_json_schema(), indent=2)
        serializer_system = f"{self.prompt_compiler.global_policy}\n\nTASK: JSON SERIALIZER\n{serializer_template}"
        serializer_user = (
            f"<schema>\n{schema_json_desc}\n</schema>\n\n"
            f"<analysis>\n{analysis_prose}\n</analysis>\n\n"
            "Return only the valid JSON object conforming strictly to the schema."
        )

        model = self._select_model(capability)
        retry_count = 0
        fields_nulled = 0
        parse_ok = False
        parsed_dict: Dict[str, Any] = {}

        ev_text = " ".join([f"{ev.text or ''} {str(ev.value or '')}" for ev in evidence_list])
        if site_facts:
            ev_text += " " + str(site_facts)
        # Never merge unverified Pass-1 LLM prose into ev_text before number grounding;
        # numbers must trace to crawled evidence or deterministic site facts only.

        try:
            resp = await self._generate_chat_completion(
                model=model,
                system_prompt=serializer_system,
                user_prompt=serializer_user,
                temperature=0.0,
                max_tokens=settings.LLM_MAX_TOKENS
            )
            self._record_llm_call(
                response=resp,
                capability=capability,
                model=model,
                system_prompt=serializer_system,
                user_prompt=serializer_user,
                agent_id=agent_role,
            )
            raw_parsed = repair_and_parse_json(resp.get("content", "")) or {}
            
            # Validate with Pydantic
            try:
                validated = schema_cls.model_validate(raw_parsed)
                parsed_dict = validated.model_dump()
                parse_ok = True
            except ValidationError as ve:
                retry_count += 1
                logger.info("Retrying serializer on ValidationError: %s", ve)
                retry_user = (
                    f"{serializer_user}\n\n"
                    f"Previous attempt produced validation error:\n{ve}\n"
                    "Fix the errors above and return the corrected JSON object."
                )
                retry_resp = await self._generate_chat_completion(
                    model=model,
                    system_prompt=serializer_system,
                    user_prompt=retry_user,
                    temperature=0.0,
                    max_tokens=settings.LLM_MAX_TOKENS
                )
                self._record_llm_call(
                    response=retry_resp,
                    capability=capability,
                    model=model,
                    system_prompt=serializer_system,
                    user_prompt=retry_user,
                    agent_id=agent_role,
                )
                raw_parsed_retry = repair_and_parse_json(retry_resp.get("content", "")) or {}
                try:
                    validated = schema_cls.model_validate(raw_parsed_retry)
                    parsed_dict = validated.model_dump()
                    parse_ok = True
                except ValidationError as ve2:
                    logger.warning("Serializer retry still invalid: %s. Using partial dump.", ve2)
                    parsed_dict = raw_parsed_retry if isinstance(raw_parsed_retry, dict) else {}
                    fields_nulled += len(ve2.errors())
        except Exception as ex:
            logger.error("Error in run_reason_then_json serializer pass: %s", ex)
            parsed_dict = {}

        # Strip ungrounded numbers
        parsed_dict = strip_ungrounded_numbers(parsed_dict, ev_text)

        # Code-assign claim IDs
        if "claims" in parsed_dict and isinstance(parsed_dict["claims"], list):
            for idx, cl in enumerate(parsed_dict["claims"], start=1):
                if isinstance(cl, dict) and not cl.get("claim_id"):
                    cl["claim_id"] = f"claim_{idx:02d}"

        logger.info(
            "run_reason_then_json completed for agent '%s': parse_ok=%s, retry_count=%s, fields_nulled=%s",
            agent_role, parse_ok, retry_count, fields_nulled
        )
        return parsed_dict
