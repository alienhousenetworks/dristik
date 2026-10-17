"""Working memory for one analysis run.

Evidence, the evidence graph, and claims stay on the blackboard.
"""
from __future__ import annotations

from app.orchestration.cognition.blackboard import CognitiveBlackboard


class RunMemory:
    def __init__(self, blackboard: CognitiveBlackboard):
        self.blackboard = blackboard

    @property
    def evidence(self):
        return self.blackboard.evidence_store

    @property
    def graph(self):
        return self.blackboard.evidence_graph

    @property
    def claims(self):
        return self.blackboard.claim_registry
