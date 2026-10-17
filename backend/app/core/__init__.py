"""Settings, security, privacy, policy, observability, and multi-LLM inference engine."""
import sys
from app.core import observability
from app.core.observability import audit_log, audit_logs, logging, metrics, tracing

sys.modules["app.observability"] = observability
sys.modules["app.observability.audit_log"] = audit_log
sys.modules["app.observability.audit_logs"] = audit_logs
sys.modules["app.observability.logging"] = logging
sys.modules["app.observability.metrics"] = metrics
sys.modules["app.observability.tracing"] = tracing

from app.core import inference
from app.core.inference import (
    budget_manager,
    fallback,
    global_policy,
    json_repair,
    llm_client,
    model_router,
    pricing,
    prompt_compiler,
    telemetry,
    together,
    prompts,
    schemas,
)

sys.modules["app.inference"] = inference
sys.modules["app.inference.budget_manager"] = budget_manager
sys.modules["app.inference.fallback"] = fallback
sys.modules["app.inference.global_policy"] = global_policy
sys.modules["app.inference.json_repair"] = json_repair
sys.modules["app.inference.llm_client"] = llm_client
sys.modules["app.inference.model_router"] = model_router
sys.modules["app.inference.pricing"] = pricing
sys.modules["app.inference.prompt_compiler"] = prompt_compiler
sys.modules["app.inference.telemetry"] = telemetry
sys.modules["app.inference.together"] = together
sys.modules["app.inference.prompts"] = prompts
sys.modules["app.inference.schemas"] = schemas

__all__ = ["observability", "inference"]
