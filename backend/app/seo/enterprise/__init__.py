"""Enterprise SEO layer.

Bounded specialists, versioned rules, and report cards sit on the sealed
SEO crawl. This package does not score AEO, GEO, or CRO, and it does not
invent a score when a check was not run.
"""

from app.seo.enterprise.assess import build_enterprise_seo
from app.seo.enterprise.agents import AGENT_CATALOG, execution_order
from app.seo.enterprise.contracts import EnterpriseSeoAssessment

__all__ = [
    "AGENT_CATALOG",
    "EnterpriseSeoAssessment",
    "build_enterprise_seo",
    "execution_order",
]
