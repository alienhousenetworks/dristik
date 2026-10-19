from typing import Any, Dict

class SEOAuditOrchestrator:
    """Legacy driver. It does not crawl, score, or invent an audit result.

    The enterprise assessment is build_enterprise_seo on a sealed report.
    """
    def __init__(self, audit_id: str, domain: str):
        self.audit_id = audit_id
        self.domain = domain

    async def run(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "domain": self.domain,
            "status": "NOT_AN_AUDIT",
            "total_agents": 35,
            "executed_agents": 0,
            "execution_time_sec": 0.0,
            "overall_score": None,
            "note": "Scores are not calculated here. Build the enterprise assessment from a sealed report.",
        }
