"""
Dristik AI Standardized Cognitive Worker Contract
Base class for the 8 reusable cognitive workers in the autonomous workforce.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.inference.model_router import ModelRouter
from app.cognition.blackboard import CognitiveBlackboard

class WorkerContext(BaseModel):
    worker_id: str
    role_name: str
    capability_id: str
    confidence_threshold: float = 0.85
    model_policy: str = "BALANCED"  # ECONOMY, BALANCED, DEEP, ENTERPRISE
    budget_remaining: float = 0.50
    constraints: List[str] = Field(default_factory=list)

class BaseCognitiveWorker(ABC):
    def __init__(self, worker_id: str, role_name: str, model_router: ModelRouter):
        self.worker_id = worker_id
        self.role_name = role_name
        self.model_router = model_router

    @abstractmethod
    async def execute_task(
        self,
        capability_id: str,
        blackboard: CognitiveBlackboard,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a capability task using structured inference and writes results to the blackboard.
        """
        pass

    def create_context(self, capability_id: str, threshold: float = 0.85, policy: str = "BALANCED") -> WorkerContext:
        return WorkerContext(
            worker_id=self.worker_id,
            role_name=self.role_name,
            capability_id=capability_id,
            confidence_threshold=threshold,
            model_policy=policy
        )
