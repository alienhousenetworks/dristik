"""Pillar modules own the classes the registry constructs."""
from app.aeo import AeoPillar
from app.cro import CroPillar
from app.pillars.crawling.pillar import CrawlingPillar
from app.geo import GeoPillar
from app.pillars.registry import PILLAR_REGISTRY, get_pillar
from app.pillars.remediation.pillar import RemediationPillar
from app.pillars.reporting.pillar import ReportingPillar
from app.seo import SeoPillar
from app.domain.pillar import PillarId


def test_registry_points_at_pillar_modules():
    expected = {
        PillarId.CRAWLING: CrawlingPillar,
        PillarId.SEO: SeoPillar,
        PillarId.GEO: GeoPillar,
        PillarId.AEO: AeoPillar,
        PillarId.CRO: CroPillar,
        PillarId.REMEDIATION: RemediationPillar,
        PillarId.REPORTING: ReportingPillar,
    }
    assert PILLAR_REGISTRY == expected
    assert get_pillar(PillarId.SEO).pillar_id == PillarId.SEO


def test_canonical_agent_modules_match_shims():
    from app.cro import CroConversionAgent as CanonicalCro
    from app.agents.discovery.brand_discovery import BrandPerspectiveAgent as CanonicalBrand
    from app.agents.discovery.brand_perspective_agent import BrandPerspectiveAgent as LegacyBrand
    from app.agents.runtime.base import BaseAgent as LegacyBase
    from app.agents.runtime.base_agent import BaseAgent as CanonicalBase
    from app.agents.runtime.reasoner import TechnicalReasonerAgent as CanonicalReasoner
    from app.agents.runtime.reasoners import TechnicalReasonerAgent as LegacyReasoner

    assert CanonicalCro().agent_id == "cro.conversion.v3"
    assert CanonicalBrand is LegacyBrand
    assert CanonicalBase is LegacyBase
    assert CanonicalReasoner is LegacyReasoner
