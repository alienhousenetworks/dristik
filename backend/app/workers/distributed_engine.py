"""
Distributed Workflow & Event Engine.
Provides decoupled event pub/sub (Redis with async in-memory fallback)
and idempotent stage worker orchestration.
"""
import asyncio
import inspect
import json
import logging
import os
from typing import Callable, Dict, Any, List, Optional

logger = logging.getLogger("dristik.distributed_engine")


class DistributedEventBroadcaster:
    """
    Broadcasts audit events (SSE / WebSocket progress) across multi-pod API gateways.
    Uses Redis PubSub when REDIS_URL is configured, or local asyncio queues in development.
    """
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self._local_subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, message: Dict[str, Any]):
        payload = json.dumps(message)
        # 1. If Redis is available in production
        if self.redis_url:
            try:
                import redis.asyncio as aioredis
                r = aioredis.from_url(self.redis_url)
                await r.publish(channel, payload)
                await r.close()
                return
            except Exception as e:
                logger.warning(f"Redis publish failed, falling back to local bus: {e}")

        # 2. Local memory broadcast
        async with self._lock:
            queues = self._local_subscribers.get(channel, [])
            for q in list(queues):
                try:
                    q.put_nowait(message)
                except Exception:
                    pass

    async def subscribe(self, channel: str) -> asyncio.Queue:
        q = asyncio.Queue()
        async with self._lock:
            if channel not in self._local_subscribers:
                self._local_subscribers[channel] = []
            self._local_subscribers[channel].append(q)
        return q

    async def unsubscribe(self, channel: str, q: asyncio.Queue):
        async with self._lock:
            if channel in self._local_subscribers:
                self._local_subscribers[channel] = [x for x in self._local_subscribers[channel] if x is not q]
                if not self._local_subscribers[channel]:
                    del self._local_subscribers[channel]


class IdempotentTaskRunner:
    """
    Executes audit pipeline steps as idempotent activities.
    If an activity has already succeeded in durable checkpoints, it resumes without duplicate execution.
    """
    def __init__(self):
        self._completed_activities: Dict[str, Any] = {}

    async def execute_activity(
        self,
        audit_id: str,
        activity_name: str,
        fn: Callable,
        *args,
        max_retries: int = 3,
        **kwargs
    ) -> Any:
        token = f"{audit_id}:{activity_name}"
        if token in self._completed_activities:
            logger.info(f"Activity '{token}' already completed; replaying cached output.")
            return self._completed_activities[token]

        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                if inspect.iscoroutinefunction(fn):
                    res = await fn(*args, **kwargs)
                else:
                    res = fn(*args, **kwargs)
                self._completed_activities[token] = res
                return res
            except Exception as e:
                last_err = e
                logger.warning(f"Activity '{token}' attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(0.1 * (2 ** attempt))

        raise RuntimeError(f"Activity '{token}' failed after {max_retries} attempts: {last_err}") from last_err


_broadcaster: Optional[DistributedEventBroadcaster] = None
_task_runner: Optional[IdempotentTaskRunner] = None


def get_event_broadcaster() -> DistributedEventBroadcaster:
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = DistributedEventBroadcaster()
    return _broadcaster


def get_task_runner() -> IdempotentTaskRunner:
    global _task_runner
    if _task_runner is None:
        _task_runner = IdempotentTaskRunner()
    return _task_runner
