"""
Dristik Modular Monolith: SEO Master Audit Engine.

Houses the 30-agent SEO audit DAG, crawler routers, discovery engines,
evidence ledgers, scorecards, and remediation pipelines.
"""
from app.seo.audit.contracts import AgentOutput, FindingContract
from app.seo.audit.orchestrator import SEOAuditOrchestrator
from app.seo.audit.audit_pipeline import execute_audit_pipeline
from app.seo.audit.orchestration.dag import AuditDAG, DAGNode
from app.seo.audit.scoring.score_engine import ScoreEngine
from app.seo.audit.scoring.seo_scorecard import SEOScorecard

__all__ = [
    "AgentOutput",
    "FindingContract",
    "SEOAuditOrchestrator",
    "execute_audit_pipeline",
    "AuditDAG",
    "DAGNode",
    "ScoreEngine",
    "SEOScorecard",
]
