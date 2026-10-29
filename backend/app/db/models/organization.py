# from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    plan = Column(String(50), default="enterprise")
    sso_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
