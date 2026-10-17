# from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class AgentExecution(Base):
    __tablename__ = "agent_executions"
    id = Column(String(64), primary_key=True, index=True)
    audit_id = Column(String(64), ForeignKey("audit_runs.id"), nullable=False, index=True)
    agent_id = Column(String(50), nullable=False)
    agent_name = Column(String(255), nullable=False)
    status = Column(String(50), default="PENDING") # PENDING, RUNNING, COMPLETED, FAILED
    execution_time_sec = Column(Float, default=0.0)
    inputs_hash = Column(String(64), nullable=True)
    outputs_summary = Column(JSON, default=dict)
    error_message = Column(String(1024), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
