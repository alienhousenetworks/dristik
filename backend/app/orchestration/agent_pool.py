"""
35-agent workforce pool and dependency DAG executor.

Instantiates every specialist in SPECIALIST_AGENTS_V3 and runs them in
topological waves. Independent agents in a wave run concurrently.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.agents.runtime.registry import SPECIALIST_AGENTS_V3, AgentDefinition, get_agent_definition
from app.agents.runtime.specialist import SpecialistAgent
from app.cognition.blackboard import CognitiveBlackboard

ProgressCb = Optional[Callable[[str, int, str, Dict[str, Any]], Awaitable[None]]]


def topological_waves(definitions: Dict[str, AgentDefinition]) -> List[List[str]]:
    """Kahn waves: agents whose dependencies are already scheduled go in the next wave."""
    ids = list(definitions.keys())
    id_set = set(ids)
    incoming: Dict[str, int] = {i: 0 for i in ids}
    edges: Dict[str, List[str]] = defaultdict(list)
    for aid, defn in definitions.items():
        for dep in defn.dependencies or []:
            if dep in id_set:
                edges[dep].append(aid)
                incoming[aid] += 1

    ready = deque([i for i in ids if incoming[i] == 0])
    waves: List[List[str]] = []
    seen = 0
    while ready:
        wave = list(ready)
        ready.clear()
        waves.append(wave)
        seen += len(wave)
        nxt: List[str] = []
        for node in wave:
            for child in edges[node]:
                incoming[child] -= 1
                if incoming[child] == 0:
                    nxt.append(child)
        ready.extend(nxt)

    if seen < len(ids):
        leftover = [i for i in ids if all(i not in w for w in waves)]
        if leftover:
            waves.append(leftover)
    return waves


class AgentPool:
    """Creates and runs the full 35-agent specialist workforce."""

    def __init__(self, model_router):
        self.model_router = model_router
        self.agents: Dict[str, SpecialistAgent] = {
            agent_id: SpecialistAgent(defn, model_router)
            for agent_id, defn in SPECIALIST_AGENTS_V3.items()
        }
        self.waves = topological_waves(SPECIALIST_AGENTS_V3)

    def __len__(self) -> int:
        return len(self.agents)

    def get(self, agent_id: str) -> Optional[SpecialistAgent]:
        if agent_id in self.agents:
            return self.agents[agent_id]
        defn = get_agent_definition(agent_id)
        if defn and defn.agent_id in self.agents:
            return self.agents[defn.agent_id]
        return None

    async def execute_all(
        self,
        blackboard: CognitiveBlackboard,
        progress_cb: ProgressCb = None,
        base_progress: int = 40,
        end_progress: int = 88,
    ) -> Dict[str, Any]:
        total = max(len(self.agents), 1)
        completed = 0
        summary: Dict[str, Any] = {
            "agents_declared": total,
            "agents_ran": 0,
            "completed": 0,
            "unavailable": 0,
            "errors": 0,
            "waves": len(self.waves),
            "results": {},
        }

        for wave_index, wave in enumerate(self.waves):
            tasks = [self._run_one(agent_id, blackboard) for agent_id in wave]
            packed = await asyncio.gather(*tasks, return_exceptions=True)
            for agent_id, payload in zip(wave, packed):
                completed += 1
                if isinstance(payload, Exception):
                    record = {
                        "agent_id": agent_id,
                        "status": "error",
                        "unavailable_reason": str(payload),
                        "claims": [],
                    }
                    blackboard.blackboard_state.setdefault("agent_results", {})[agent_id] = record
                    summary["errors"] += 1
                    summary["results"][agent_id] = record
                else:
                    status = (payload or {}).get("status")
                    summary["agents_ran"] += 1
                    if status == "unavailable":
                        summary["unavailable"] += 1
                    elif status == "error":
                        summary["errors"] += 1
                    else:
                        summary["completed"] += 1
                    summary["results"][agent_id] = payload

                if progress_cb:
                    pct = base_progress + int((completed / total) * (end_progress - base_progress))
                    name = SPECIALIST_AGENTS_V3[agent_id].agent_name
                    await progress_cb(
                        "specialist_execution",
                        pct,
                        f"Specialist {completed}/{total}: {name}",
                        {
                            "agent_id": agent_id,
                            "wave": wave_index + 1,
                            "waves": len(self.waves),
                            "status": summary["results"][agent_id].get("status"),
                        },
                    )

        blackboard.blackboard_state["agent_pool_summary"] = {
            k: summary[k] for k in ("agents_declared", "agents_ran", "completed", "unavailable", "errors", "waves")
        }
        return summary

    async def _run_one(self, agent_id: str, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        agent = self.agents[agent_id]
        return await agent.run(blackboard)
