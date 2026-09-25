"""
Dristik AI Temporal Intelligence & Audit Timeline
Tracks historical snapshots of audits, scores, and findings to answer:
'What changed? What improved? What became worse? Which recommendations were implemented?'
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.domain.models import OverallScoreResult, Finding, CodePatch

class AuditSnapshot(BaseModel):
    snapshot_id: str
    audit_id: str
    domain: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    overall_score: float
    grade: str
    findings_count: int
    critical_findings_count: int
    top_findings: List[str] = Field(default_factory=list)
    resolved_findings: List[str] = Field(default_factory=list)

class TimelineDelta(BaseModel):
    score_change: float
    grade_change: str
    new_findings: List[str] = Field(default_factory=list)
    resolved_findings: List[str] = Field(default_factory=list)
    summary: str

class WebsiteIntelligenceTimeline:
    """
    Maintains historical timeline of audit snapshots for a domain.
    """

    def __init__(self, domain: str):
        self.domain = domain
        self.snapshots: List[AuditSnapshot] = []

    def record_audit(
        self,
        audit_id: str,
        scores: OverallScoreResult,
        findings: List[Finding]
    ) -> AuditSnapshot:
        crit_count = sum(1 for f in findings if f.severity == "CRITICAL")
        snapshot = AuditSnapshot(
            snapshot_id=f"snap_{len(self.snapshots) + 1:03d}",
            audit_id=audit_id,
            domain=self.domain,
            overall_score=scores.overall_score,
            grade=scores.grade,
            findings_count=len(findings),
            critical_findings_count=crit_count,
            top_findings=[f.title for f in findings[:5]]
        )
        self.snapshots.append(snapshot)
        return snapshot

    def compute_delta(self) -> Optional[TimelineDelta]:
        if len(self.snapshots) < 2:
            return None

        prev = self.snapshots[-2]
        curr = self.snapshots[-1]

        score_diff = round(curr.overall_score - prev.overall_score, 1)
        prev_set = set(prev.top_findings)
        curr_set = set(curr.top_findings)

        new_issues = list(curr_set - prev_set)
        resolved_issues = list(prev_set - curr_set)

        direction = "improved" if score_diff > 0 else ("declined" if score_diff < 0 else "held steady")
        summary = f"Website health score {direction} by {abs(score_diff)} points ({prev.grade} -> {curr.grade})."

        return TimelineDelta(
            score_change=score_diff,
            grade_change=f"{prev.grade} -> {curr.grade}",
            new_findings=new_issues,
            resolved_findings=resolved_issues,
            summary=summary
        )
