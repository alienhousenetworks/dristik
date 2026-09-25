"""
Dristik AI Dynamic Team Builder & Worker Pool Manager
Dynamically provisions reusable workers into specialist teams (Technical, Business, GEO, AI Search, UX, Verification)
and executes planned capability tasks in parallel.
"""
import asyncio
from typing import Dict, Any, List, Optional
from app.inference.model_router import ModelRouter
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.capability import CAPABILITY_REGISTRY, CapabilityDomain
from app.domain.models import CrawlManifest
from app.orchestration.capability_router import CapabilityRouter
from app.workers.analyst_worker import CognitiveAnalystWorker
from app.workers.research_worker import CognitiveResearchWorker
from app.workers.critic_worker import CognitiveCriticWorker
from app.workers.synthesizer_worker import CognitiveSynthesizerWorker

class DynamicTeamBuilder:
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        self.capability_router = CapabilityRouter()
        
        # Provision Reusable Worker Pool
        self.worker_analyst_1 = CognitiveAnalystWorker("worker_analyst_1", model_router)
        self.worker_analyst_2 = CognitiveAnalystWorker("worker_analyst_2", model_router)
        self.worker_researcher = CognitiveResearchWorker("worker_researcher", model_router)
        self.worker_critic = CognitiveCriticWorker("worker_critic", model_router)
        self.worker_synthesizer = CognitiveSynthesizerWorker("worker_synthesizer", model_router)

    async def execute_team_capabilities(
        self,
        capability_ids: List[str],
        manifest: CrawlManifest,
        blackboard: CognitiveBlackboard
    ) -> Dict[str, Any]:
        """
        Executes a set of capability IDs using optimal workers (deterministic vs cognitive).
        """
        results = {}
        async_tasks = []

        for cap_id in capability_ids:
            spec = CAPABILITY_REGISTRY.get(cap_id)
            if not spec:
                continue

            # Deterministic ($0 inference)
            if self.capability_router.is_deterministic(cap_id):
                det_results = self.capability_router.execute_deterministic_capability(cap_id, manifest, blackboard)
                for r in det_results:
                    blackboard.claim_registry.register_claim(
                        agent_id=f"deterministic_{cap_id}",
                        statement=r["statement"],
                        category=r["category"],
                        severity=r["severity"],
                        confidence=r["confidence"],
                        recommendation=r["recommendation"]
                    )
                results[cap_id] = {"type": "deterministic", "claims_count": len(det_results)}
            
            # Cognitive SLM / Reasoning
            else:
                worker = self._assign_worker(cap_id)
                if worker:
                    async_tasks.append(self._run_worker_safe(worker, cap_id, blackboard))

        if async_tasks:
            worker_results = await asyncio.gather(*async_tasks, return_exceptions=True)
            for r in worker_results:
                if isinstance(r, dict) and "capability_id" in r:
                    results[r["capability_id"]] = r

        return results

    def _assign_worker(self, capability_id: str):
        spec = CAPABILITY_REGISTRY.get(capability_id)
        if not spec:
            return self.worker_analyst_1

        if spec.domain == CapabilityDomain.AI_SEARCH:
            return self.worker_researcher
        elif spec.domain == CapabilityDomain.VERIFICATION:
            return self.worker_critic
        elif spec.domain in [CapabilityDomain.BUSINESS, CapabilityDomain.CONTENT]:
            return self.worker_analyst_1
        elif spec.domain in [CapabilityDomain.GEO, CapabilityDomain.EXPERIENCE]:
            return self.worker_analyst_2
        return self.worker_analyst_1

    async def _run_worker_safe(self, worker, capability_id: str, blackboard: CognitiveBlackboard):
        try:
            res = await worker.execute_task(capability_id, blackboard)
            return {"capability_id": capability_id, "status": "success", "result": res}
        except Exception as e:
            return {"capability_id": capability_id, "status": "error", "error": str(e)}
