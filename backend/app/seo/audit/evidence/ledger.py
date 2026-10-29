import hashlib
from typing import Dict, Any

class EvidenceLedger:
    def __init__(self):
        self.ledger = []

    def record(self, entry: Dict[str, Any]) -> str:
        h = hashlib.sha256(str(entry).encode('utf-8')).hexdigest()
        entry['hash'] = h
        self.ledger.append(entry)
        return h
