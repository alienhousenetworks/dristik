from typing import List, Dict, Any, Optional

class EvidenceStore:
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def put(self, evidence_id: str, data: Dict[str, Any]):
        self._store[evidence_id] = data

    def get(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(evidence_id)
