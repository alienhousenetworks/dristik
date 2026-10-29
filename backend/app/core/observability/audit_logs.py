from typing import Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger("dristik.audit_logs")

def log_audit_event(event_type: str, user_id: str, payload: Dict[str, Any]):
    logger.info(f"[AUDIT_LOG] event={event_type} user={user_id} data={payload}")
