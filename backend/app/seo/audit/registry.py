from typing import Dict, Any, Callable

class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Dict[str, Any]] = {}

    def register(self, agent_id: str, name: str, stage: str, runner: Callable):
        self._agents[agent_id] = {
            "id": agent_id,
            "name": name,
            "stage": stage,
            "runner": runner
        }

    def get(self, agent_id: str) -> Dict[str, Any]:
        return self._agents.get(agent_id)

    def list_all(self):
        return list(self._agents.values())

agent_registry = AgentRegistry()
