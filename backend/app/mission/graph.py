"""
Dristik AI Stateful Mission Execution Graph Engine
Provides LangGraph-compatible stateful DAG orchestration, explicit transitions,
conditional routing, bounded reflection cycles, event-driven streaming, and human approval gates.
"""
import asyncio
import inspect
from typing import Dict, Any, Callable, List, Optional, Union, Awaitable
from datetime import datetime

from app.mission.state import MissionState
from app.domain.enums import AnalysisStage

START = "__START__"
END = "__END__"

class StateGraph:
    """
    Asynchronous state machine graph engine with conditional branching,
    loops, human approval checkpoints, and event emission.
    """

    def __init__(self, state_schema=MissionState):
        self.state_schema = state_schema
        self.nodes: Dict[str, Callable[[MissionState], Awaitable[Union[MissionState, Dict[str, Any], None]]]] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, tuple[Callable[[MissionState], str], Dict[str, str]]] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, action: Callable[[MissionState], Awaitable[Union[MissionState, Dict[str, Any], None]]]):
        if name in (START, END):
            raise ValueError(f"Reserved node name: {name}")
        self.nodes[name] = action

    def add_edge(self, start_key: str, end_key: str):
        self.edges[start_key] = end_key

    def add_conditional_edges(
        self,
        source: str,
        path: Callable[[MissionState], str],
        path_map: Dict[str, str]
    ):
        self.conditional_edges[source] = (path, path_map)

    def set_entry_point(self, key: str):
        self.entry_point = key

    def compile(self) -> "CompiledStateGraph":
        if not self.entry_point and START not in self.edges:
            raise ValueError("Entry point must be set or edge from START must exist.")
        entry = self.entry_point or self.edges[START]
        return CompiledStateGraph(
            nodes=self.nodes,
            edges=self.edges,
            conditional_edges=self.conditional_edges,
            entry_point=entry
        )

class CompiledStateGraph:
    def __init__(
        self,
        nodes: Dict[str, Callable],
        edges: Dict[str, str],
        conditional_edges: Dict[str, tuple[Callable, Dict[str, str]]],
        entry_point: str
    ):
        self.nodes = nodes
        self.edges = edges
        self.conditional_edges = conditional_edges
        self.entry_point = entry_point

    async def astream(
        self,
        initial_state: MissionState,
        event_callback: Optional[Callable[[str, str, int, str, Dict[str, Any]], Awaitable[None]]] = None
    ) -> MissionState:
        """
        Executes the graph node-by-node, broadcasting real-time events and handling transitions.
        """
        state = initial_state
        current_node_name = self.entry_point
        visited_nodes: List[str] = []
        max_steps = 40  # Guardrail against infinite loops

        step_counter = 0

        while current_node_name != END and step_counter < max_steps:
            step_counter += 1
            visited_nodes.append(current_node_name)
            state.current_node = current_node_name

            # Check if execution is paused for human-in-the-loop approval
            if state.waiting_for_approval:
                if event_callback:
                    await event_callback(
                        state.mission_id,
                        "waiting_approval",
                        90,
                        f"Paused at node '{current_node_name}' awaiting human approval ({state.approval_gate}).",
                        {"gate": state.approval_gate, "node": current_node_name}
                    )
                return state

            node_func = self.nodes.get(current_node_name)
            if not node_func:
                raise RuntimeError(f"Node '{current_node_name}' not registered in state graph.")

            # Record event: Node Started
            event_payload = {
                "node": current_node_name,
                "timestamp": datetime.now().isoformat(),
                "reflection_cycle": state.reflection_cycle
            }
            state.events.append({"event": "node_started", **event_payload})

            # Execute node
            try:
                if inspect.iscoroutinefunction(node_func):
                    update = await node_func(state)
                else:
                    update = node_func(state)

                # Merge state updates if dictionary returned
                if isinstance(update, dict):
                    for k, v in update.items():
                        if hasattr(state, k):
                            setattr(state, k, v)
                elif isinstance(update, MissionState):
                    state = update

            except Exception as e:
                state.status = AnalysisStage.FAILED
                state.error = f"Error in node '{current_node_name}': {str(e)}"
                if event_callback:
                    await event_callback(
                        state.mission_id,
                        "failed",
                        100,
                        f"Execution failed at node {current_node_name}: {str(e)}",
                        {"error": str(e), "node": current_node_name}
                    )
                raise e

            # Record event: Node Completed
            state.events.append({
                "event": "node_completed",
                "node": current_node_name,
                "timestamp": datetime.now().isoformat()
            })

            # Check for early termination condition (e.g. Budget exhausted)
            if state.budget.spent_usd > state.budget.max_budget_usd:
                state.events.append({"event": "budget_limit_reached", "spent": state.budget.spent_usd})
                current_node_name = END
                break

            # Route to next node
            if current_node_name in self.conditional_edges:
                route_fn, path_map = self.conditional_edges[current_node_name]
                route_key = route_fn(state)
                next_node = path_map.get(route_key, END)
                current_node_name = next_node
            elif current_node_name in self.edges:
                current_node_name = self.edges[current_node_name]
            else:
                current_node_name = END

        return state
