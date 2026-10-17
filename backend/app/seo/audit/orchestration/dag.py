from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from app.core.enums import AuditStage

@dataclass
class DAGNode:
    agent_id: str
    agent_name: str
    stage: AuditStage
    dependencies: List[str] = field(default_factory=list)
    description: str = ""

class AuditDAG:
    """Defines the 30-agent dependency Directed Acyclic Graph."""
    def __init__(self):
        self.nodes: Dict[str, DAGNode] = {}
        self._build_master_dag()

    def add_node(self, node: DAGNode):
        self.nodes[node.agent_id] = node

    def _build_master_dag(self):
        self.add_node(DAGNode("01", "Audit Orchestrator", AuditStage.STAGE_1_PLAN, []))
        self.add_node(DAGNode("02", "Evidence Integrity Guard", AuditStage.STAGE_1_PLAN, ["01"]))
        self.add_node(DAGNode("03", "Crawling & Discovery", AuditStage.STAGE_2_CRAWL, ["02"]))
        for i in range(4, 9):
            self.add_node(DAGNode(f"{i:02d}", f"Technical Agent {i}", AuditStage.STAGE_3_TECHNICAL, ["03"]))
        for i in range(9, 15):
            self.add_node(DAGNode(f"{i:02d}", f"Content Agent {i}", AuditStage.STAGE_4_CONTENT, ["04"]))
        for i in range(15, 20):
            self.add_node(DAGNode(f"{i:02d}", f"Authority Agent {i}", AuditStage.STAGE_5_AUTHORITY, ["03"]))
        for i in range(20, 23):
            self.add_node(DAGNode(f"{i:02d}", f"GEO/AEO Agent {i}", AuditStage.STAGE_6_GEO_AEO, ["04", "10"]))
        for i in range(23, 27):
            self.add_node(DAGNode(f"{i:02d}", f"Business/Risk Agent {i}", AuditStage.STAGE_7_BUSINESS, ["07", "11"]))
        for i in range(27, 31):
            self.add_node(DAGNode(f"{i:02d}", f"Synthesis/Delivery Agent {i}", AuditStage.STAGE_8_SYNTHESIS, ["26"]))

    def get_ready_nodes(self, completed_ids: Set[str]) -> List[DAGNode]:
        ready = []
        for node in self.nodes.values():
            if node.agent_id not in completed_ids:
                if all(dep in completed_ids for dep in node.dependencies):
                    ready.append(node)
        return ready
