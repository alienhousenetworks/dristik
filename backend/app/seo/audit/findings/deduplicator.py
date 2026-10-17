from typing import List, Dict, Any

class FindingDeduplicator:
    def deduplicate(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for f in findings:
            key = (f.get("category"), f.get("title"))
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique
