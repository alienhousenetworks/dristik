"""
Task Executor with Idempotency, Timeouts, Exponential Retry, Evidence-Hash Caching,
Token/Cost Tracking, and State Checkpointing.
Fail-closed: unregistered runners are never silently treated as successful no-ops.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from app.seo.audit.orchestration.dag import DAGNode
from app.seo.audit.orchestration.execution_state import NodeState, TaskCheckpoint


class TaskExecutor:
    """
    Executes an individual DAG task with timeouts, exponential retries,
    evidence-hash result caching, and checkpointing.
    """

    def __init__(self, task_runners: Optional[Dict[str, Callable]] = None):
        self.task_runners = task_runners or {}
        self._result_cache: Dict[str, Dict[str, Any]] = {}

    def register_runner(self, agent_id: str, runner: Callable) -> None:
        self.task_runners[agent_id] = runner

    def has_runner(self, agent_id: str) -> bool:
        return agent_id in self.task_runners

    @staticmethod
    def compute_inputs_hash(data: Any) -> str:
        try:
            serialized = json.dumps(data, sort_keys=True, default=str)
        except Exception:
            serialized = str(data)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]

    async def execute_task(
        self,
        node: DAGNode,
        context: Dict[str, Any],
        on_retry: Optional[Callable[[str, int, Exception], None]] = None,
    ) -> TaskCheckpoint:
        task_id = node.agent_id
        runner = self.task_runners.get(task_id)
        inputs_hash = self.compute_inputs_hash({
            "agent_id": task_id,
            "target_url": context.get("target_url"),
            "mode": str(context.get("mode")),
            "evidence_hash": context.get("evidence_hash"),
        })

        # Evidence-hash cache hit for idempotent AI/deterministic reuse
        cache_key = f"{task_id}:{inputs_hash}"
        if context.get("enable_cache") and cache_key in self._result_cache:
            cached_out = self._result_cache[cache_key]
            return TaskCheckpoint(
                task_id=task_id,
                agent_id=task_id,
                status=NodeState.COMPLETED,
                inputs_hash=inputs_hash,
                output_summary=cached_out,
                findings_count=len(cached_out.get("findings", [])) if isinstance(cached_out, dict) else 0,
                execution_time_sec=0.0,
                token_usage=0,
                estimated_cost_usd=0.0,
                cached=True,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

        if runner is None:
            return TaskCheckpoint(
                task_id=task_id,
                agent_id=task_id,
                status=NodeState.FAILED,
                inputs_hash=inputs_hash,
                error_message=f"ConfigurationError: No executable runner registered for DAG node '{task_id}'",
                execution_time_sec=0.0,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

        retries = 0
        backoff = 0.25
        start_time = time.monotonic()

        while True:
            try:
                output_data = await asyncio.wait_for(
                    runner(context),
                    timeout=node.timeout_sec,
                )

                elapsed = time.monotonic() - start_time
                out_dict = output_data if isinstance(output_data, dict) else {"result": str(output_data)}
                status_str = str(out_dict.get("node_status") or "").upper()
                node_state = NodeState.SKIPPED if status_str in ("SKIPPED", "DATA_UNAVAILABLE", "NOT_APPLICABLE") else NodeState.COMPLETED
                findings_count = len(out_dict.get("findings", [])) if isinstance(out_dict.get("findings"), list) else 0
                token_usage = int(out_dict.get("token_usage") or 0)
                cost_usd = float(out_dict.get("estimated_cost_usd") or 0.0)

                if context.get("enable_cache") and node_state == NodeState.COMPLETED:
                    self._result_cache[cache_key] = out_dict

                return TaskCheckpoint(
                    task_id=task_id,
                    agent_id=task_id,
                    status=node_state,
                    inputs_hash=inputs_hash,
                    output_summary=out_dict,
                    findings_count=findings_count,
                    execution_time_sec=round(elapsed, 4),
                    token_usage=token_usage,
                    estimated_cost_usd=round(cost_usd, 6),
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )

            except Exception as exc:
                retries += 1
                if retries <= node.retry_limit:
                    if on_retry:
                        on_retry(task_id, retries, exc)
                    await asyncio.sleep(backoff)
                    backoff *= 1.5
                else:
                    elapsed = time.monotonic() - start_time
                    return TaskCheckpoint(
                        task_id=task_id,
                        agent_id=task_id,
                        status=NodeState.FAILED,
                        inputs_hash=inputs_hash,
                        error_message=f"{type(exc).__name__}: {str(exc)}",
                        execution_time_sec=round(elapsed, 4),
                        completed_at=datetime.now(timezone.utc).isoformat(),
                    )
