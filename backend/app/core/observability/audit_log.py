"""Security audit log entry point."""
from app.core.observability.audit_logs import log_audit_event

__all__ = ["log_audit_event"]
