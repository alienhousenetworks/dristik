import asyncio
from typing import List, Set
from app.seo.audit.orchestration.dag import AuditDAG

class DAGScheduler:
    def __init__(self, dag: AuditDAG):
        self.dag = dag
        self.completed_nodes: Set[str] = set()

    def get_next_batch(self):
        return self.dag.get_ready_nodes(self.completed_nodes)

    def mark_completed(self, node_id: str):
        self.completed_nodes.add(node_id)
