from datetime import datetime, timezone
from sqlalchemy.orm import relationship, synonym
from app.db.base import Base, Column, String, Float, DateTime, ForeignKey, Text, JSON


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(64), primary_key=True, index=True)
    audit_run_id = Column(String(64), ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=True)
    category = Column(String(50), nullable=False)
    severity = Column(String(20), default="MEDIUM", nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    impact_explanation = Column(Text, nullable=True)
    remediation_advice = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    suggested_patch = Column(JSON, nullable=True)
    jira_issue_key = Column(String(50), nullable=True)
    github_pr_url = Column(Text, nullable=True)
    status = Column(String(50), default="open", nullable=False)
    remediation_status = Column(String(50), default="OPEN", nullable=True)
    confidence = Column(Float, default=1.0, nullable=True)
    evidence_ids = Column(JSON, default=list, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Backward compatibility synonym for code expecting .audit_id
    audit_id = synonym("audit_run_id")

    # Relationships
    audit_run = relationship("AuditRun", back_populates="findings")
