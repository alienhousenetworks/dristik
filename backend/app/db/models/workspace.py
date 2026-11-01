from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, DateTime, ForeignKey


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True, index=True)
    org_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_workspaces_org_slug"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="workspaces")
    domains = relationship("Domain", back_populates="workspace", cascade="all, delete-orphan")
