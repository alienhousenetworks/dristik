from abc import ABC, abstractmethod
from typing import Dict, Any
from app.seo.audit.contracts import AgentOutput

class BaseAgent(ABC):
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name

    @abstractmethod
    async def analyze(self, audit_context: Dict[str, Any]) -> AgentOutput:
        pass
