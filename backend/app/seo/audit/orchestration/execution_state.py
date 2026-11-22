"""
Workflow Execution States, Checkpoints, and Policies for the SEO Orchestrator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class AuditMode(str, Enum):
    QUICK = "QUICK"             # 5–25 priority URLs, 60s budget, rapid diagnostic
    STANDARD = "STANDARD"       # 100–250 URLs, 300s budget, commercial baseline
    DEEP = "DEEP"               # Up to 2,500 URLs, 1,200s budget, full JS rendering
    CONTINUOUS = "CONTINUOUS"   # Monitored URL subset, delta tracking, scheduled


class NodeState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class WorkflowStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class FailurePolicy(str, Enum):
    FAIL_FAST = "FAIL_FAST"
    ISOLATE_AND_CONTINUE = "ISOLATE_AND_CONTINUE"


@dataclass
class RetryPolicy:
    max_retries: int = 2
    backoff_factor: float = 1.5
    timeout_sec: float = 60.0


@dataclass
class WorkflowBudget:
    max_pages: int = 250
    max_execution_sec: float = 300.0
    max_cost_usd: float = 5.0
    max_concurrency: int = 5
    requests_per_second: float = 5.0

    @classmethod
    def from_mode(cls, mode: AuditMode) -> "WorkflowBudget":
        if mode == AuditMode.QUICK:
            return cls(max_pages=25, max_execution_sec=60.0, max_cost_usd=1.0, max_concurrency=3, requests_per_second=3.0)
        elif mode == AuditMode.DEEP:
            return cls(max_pages=2500, max_execution_sec=1200.0, max_cost_usd=25.0, max_concurrency=8, requests_per_second=8.0)
        elif mode == AuditMode.CONTINUOUS:
            return cls(max_pages=100, max_execution_sec=180.0, max_cost_usd=3.0, max_concurrency=4, requests_per_second=4.0)
        return cls()


class AuditConfiguration(BaseModel):
    target_url: str
    mode: AuditMode = AuditMode.STANDARD
    workspace_id: str = "ws_default"
    org_id: str = ""
    tenant_id: Optional[str] = None
    max_pages: Optional[int] = None
    respect_robots_txt: str = "OBEY"
    render_javascript: bool = True
    connectors_enabled: List[str] = Field(default_factory=list)
    excluded_paths: List[str] = Field(default_factory=list)
    custom_seed_urls: List[str] = Field(default_factory=list)
    failure_policy: FailurePolicy = FailurePolicy.ISOLATE_AND_CONTINUE
    budget: Optional[Dict[str, Any]] = None
    live_crawl: bool = False  # Opt-in live network crawl when no seed_pages/source_report provided
    idempotency_key: Optional[str] = None
    defer_remediation: bool = False  # Defer remediation when part of multi-pillar unified pipeline


AuditConfig = AuditConfiguration


@dataclass
class TaskCheckpoint:
    task_id: str
    agent_id: str
    status: NodeState
    inputs_hash: Optional[str] = None
    output_summary: Dict[str, Any] = field(default_factory=dict)
    findings_count: int = 0
    execution_time_sec: float = 0.0
    token_usage: int = 0
    estimated_cost_usd: float = 0.0
    cached: bool = False
    error_message: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class WorkflowExecutionState:
    audit_id: str
    mode: AuditMode
    status: WorkflowStatus = WorkflowStatus.QUEUED
    current_stage: str = "INIT"
    checkpoints: Dict[str, TaskCheckpoint] = field(default_factory=dict)
    active_tasks: Set[str] = field(default_factory=set)
    completed_tasks: Set[str] = field(default_factory=set)
    failed_tasks: Set[str] = field(default_factory=set)
    skipped_tasks: Set[str] = field(default_factory=set)
    crawled_pages: List[Dict[str, Any]] = field(default_factory=list)
    discovered_urls: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    elapsed_time_sec: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    cancellation_requested: bool = False
