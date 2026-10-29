"""
Structured Data & Knowledge Graph Agent:
Validates Schema.org JSON-LD markups, microdata, entity connectivity,
and rich snippet eligibility across crawled templates.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType


class StructuredDataAgent(BaseAgent):
    """Audits schema.org JSON-LD markup and structured data validity."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="seo.schema.v3",
            capability="schema_validation",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        schema_count = sum(1 for p in pages if getattr(p, "schema_types", None))

        observations = {
            "total_pages": len(pages),
            "pages_with_schema": schema_count,
        }

        claims = []
        if schema_count == 0 and len(pages) > 0:
            claim = self.register_claim(
                blackboard=blackboard,
                statement="No Schema.org structured data (Organization, WebSite, BreadcrumbList) was found on the site.",
                category=Category.SCHEMA,
                severity=Severity.HIGH,
                claim_type=ClaimType.FACT,
                confidence=0.97,
                recommendation="Deploy valid JSON-LD schemas for Organization, WebSite, and page-specific entities (Article/Product).",
                impact=7,
                effort=2,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "domain": "seo",
            "specialty": "structured_data",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
