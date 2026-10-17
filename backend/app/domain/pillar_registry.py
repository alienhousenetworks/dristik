"""
Pillar Registry: Central directory of domain pillars with lookup, lifecycle and execution helpers.
"""
from typing import Any, Dict, List, Optional, Set, Type
from app.domain.pillar import PillarId, DomainPillar
from app.crawl.pillar import CrawlingPillar
from app.seo.pillar import SeoPillar
from app.geo.pillar import GeoPillar
from app.aeo.pillar import AeoPillar
from app.cro.pillar import CroPillar
from app.remediation.pillar import RemediationPillar
from app.reports.pillar import ReportingPillar

PILLAR_REGISTRY: Dict[PillarId, Type] = {
    PillarId.CRAWLING: CrawlingPillar,
    PillarId.SEO: SeoPillar,
    PillarId.GEO: GeoPillar,
    PillarId.AEO: AeoPillar,
    PillarId.CRO: CroPillar,
    PillarId.REMEDIATION: RemediationPillar,
    PillarId.REPORTING: ReportingPillar,
}


def get_pillar(pillar_id: str | PillarId, model_router=None) -> Optional[Any]:
    try:
        p_id = PillarId(pillar_id) if isinstance(pillar_id, str) else pillar_id
    except ValueError:
        return None

    cls = PILLAR_REGISTRY.get(p_id)
    if not cls:
        return None
    if p_id in (PillarId.SEO, PillarId.GEO, PillarId.AEO, PillarId.CRO):
        return cls(model_router=model_router)
    return cls()


def list_pillars() -> List[str]:
    return [p.value for p in PILLAR_REGISTRY.keys()]


def get_pillar_domains(pillar_id: str | PillarId) -> Set[str]:
    p = get_pillar(pillar_id)
    if p and hasattr(p, "domains"):
        return set(p.domains)
    return set()


__all__ = [
    "PILLAR_REGISTRY",
    "get_pillar",
    "list_pillars",
    "get_pillar_domains",
    "CrawlingPillar",
    "SeoPillar",
    "GeoPillar",
    "AeoPillar",
    "CroPillar",
    "RemediationPillar",
    "ReportingPillar",
]
