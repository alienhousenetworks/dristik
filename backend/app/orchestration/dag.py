"""
Dristik AI Task DAG & Concurrency Engine
Defines agent dependencies and executes independent specialist agents in parallel.
"""
import asyncio
from typing import List, Dict, Any, Callable
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard

class AgentTaskNode:
    def __init__(self, agent: BaseAgent, dependencies: List[str] = None):
        self.agent = agent
        self.agent_id = agent.agent_id
        self.dependencies = dependencies or []

class TaskGraph:
    def __init__(self):
        self.nodes: Dict[str, AgentTaskNode] = {}

    def add_node(self, agent: BaseAgent, dependencies: List[str] = None):
        self.nodes[agent.agent_id] = AgentTaskNode(agent, dependencies)

    async def execute_parallel_tier(
        self,
        agent_ids: List[str],
        blackboard: CognitiveBlackboard,
        step_callback: Callable[[str, str], None] = None
    ):
        """
        Executes a tier of independent agents concurrently.
        """
        async def run_single(node_id: str):
            node = self.nodes.get(node_id)
            if not node:
                return
            if step_callback:
                step_callback(node.agent_id, "running")
            await node.agent.run(blackboard)
            if step_callback:
                step_callback(node.agent_id, "completed")

        tasks = [run_single(aid) for aid in agent_ids if aid in self.nodes]
        await asyncio.gather(*tasks, return_exceptions=True)
