from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, Integer, Boolean, DateTime, ForeignKey


class Domain(Base):
    __tablename__ = "domains"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    hostname = Column(String(255), nullable=False, index=True)
    default_scheme = Column(String(10), default="https", nullable=False)
    site_type = Column(String(50), default="b2b_saas", nullable=False)
    crawl_frequency = Column(String(50), default="weekly", nullable=False)
    max_pages = Column(Integer, default=500, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="domains")
    audit_runs = relationship("AuditRun", back_populates="domain_rel", cascade="all, delete-orphan")
    ai_citations = relationship("AICitation", back_populates="domain", cascade="all, delete-orphan")
