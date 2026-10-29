from typing import List, Dict, Any
from datetime import datetime, timezone

class EventStore:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def emit(self, event_type: str, data: Dict[str, Any]):
        self.events.append({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
