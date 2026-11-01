from datetime import datetime, timezone
from sqlalchemy.orm import relationship, synonym
from app.db.base import Base, Column, String, Boolean, DateTime, Text


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    plan = Column(String(50), default="enterprise", nullable=False)
    sso_enabled = Column(Boolean, default=False, nullable=False)
    sso_provider = Column(String(50), nullable=True)
    sso_metadata_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Backward compatibility synonym for legacy code expecting .org_id
    org_id = synonym("id")

    # Relationships
    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    enterprise_audit_logs = relationship("EnterpriseAuditLog", back_populates="organization", cascade="all, delete-orphan")
