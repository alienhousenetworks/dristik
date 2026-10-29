"""
Unit & Integration Tests for Dristik Domain-Wise Modular Pillars.
Validates PillarId, DomainPillar contracts, registry resolution, and backward compatibility.
"""
import pytest
from app.domain.pillar import PillarId, DomainPillar, PillarScoreResult
from app.domain.models import Finding
from app.pillars import (
    PILLAR_REGISTRY,
    get_pillar,
    list_pillars,
    get_pillar_domains,
)
from app.pillars.crawling import CrawlingPillar
from app.seo import SeoPillar
from app.geo import GeoPillar
from app.aeo import AeoPillar
from app.cro import CroPillar
from app.pillars.remediation import RemediationPillar
from app.pillars.reporting import ReportingPillar


def test_pillar_id_enum():
    expected_ids = {"crawling", "seo", "geo", "aeo", "cro", "remediation", "reporting"}
    actual_ids = {p.value for p in PillarId}
    assert expected_ids == actual_ids


def test_pillar_registry_completeness():
    registered = set(list_pillars())
    assert len(registered) == 7
    for pid in PillarId:
        assert pid.value in registered


def test_get_pillar_instances():
    seo_pillar = get_pillar(PillarId.SEO)
    assert isinstance(seo_pillar, SeoPillar)
    assert seo_pillar.pillar_id == PillarId.SEO
    assert "TECHNICAL_SEO" in seo_pillar.domains

    geo_pillar = get_pillar("geo")
    assert isinstance(geo_pillar, GeoPillar)
    assert geo_pillar.pillar_id == PillarId.GEO
    assert "GEO" in geo_pillar.domains

    aeo_pillar = get_pillar(PillarId.AEO)
    assert isinstance(aeo_pillar, AeoPillar)
    assert aeo_pillar.pillar_id == PillarId.AEO

    cro_pillar = get_pillar(PillarId.CRO)
    assert isinstance(cro_pillar, CroPillar)
    assert cro_pillar.pillar_id == PillarId.CRO

    crawl_pillar = get_pillar("crawling")
    assert isinstance(crawl_pillar, CrawlingPillar)
    assert crawl_pillar.pillar_id == PillarId.CRAWLING

    rem_pillar = get_pillar("remediation")
    assert isinstance(rem_pillar, RemediationPillar)

    rep_pillar = get_pillar("reporting")
    assert isinstance(rep_pillar, ReportingPillar)


def test_pillar_score_calculation():
    from app.domain.enums import Category, Severity

    seo_pillar = get_pillar(PillarId.SEO)
    findings = [
        Finding(
            finding_id="SEO-001",
            category=Category.TECHNICAL_SEO,
            title="Disallow directive blocks search crawlers",
            description="robots.txt contains disallow for main pages",
            severity=Severity.HIGH,
            confidence=0.9,
            priority=10,
            why_it_matters="Loss of indexation",
            business_impact="Traffic loss",
            root_cause="Bad robots.txt",
            expected_condition="Robots.txt permits crawl",
            recommendation="Fix robots.txt",
            validation_criteria="Validator returns 200",
        ),
        Finding(
            finding_id="SEO-002",
            category=Category.TECHNICAL_SEO,
            title="Slow LCP on key landing pages",
            description="LCP is 4.5s on mobile viewport",
            severity=Severity.MEDIUM,
            confidence=0.85,
            priority=7,
            why_it_matters="Poor Core Web Vitals",
            business_impact="Bounce rate increase",
            root_cause="Unoptimized hero images",
            expected_condition="LCP < 2.5s",
            recommendation="Use WebP and lazy loading",
            validation_criteria="Lighthouse LCP < 2.5s",
        ),
    ]
    res = seo_pillar.calculate_pillar_score(findings)
    assert isinstance(res, PillarScoreResult)
    assert res.pillar_id == PillarId.SEO
    assert res.score == 92.0
    assert res.grade == "A"
    assert res.measured_findings_count == 2


def test_backward_compatible_agent_imports():
    from app.agents.aeo import DirectAnswerAgent
    from app.agents.aeo.direct_answer_agent import DirectAnswerAgent as LegacyDirectAnswer
    from app.agents.aeo.direct_answers import DirectAnswerAgent as CanonicalDirectAnswer
    from app.cro import CroConversionAgent
    from app.geo.agents import AiSearchCitationAgent, GeoReadinessAgent
    from app.seo import ContentSeoAgent, TechnicalSeoAgent
    from app.seo.agents.technical import TechnicalSeoAgent as CanonicalTechnical
    from app.seo.agents.technical_seo_agent import TechnicalSeoAgent as LegacyTechnical
    from app.seo.pillar import SeoPillar as SeoPillarModule

    assert TechnicalSeoAgent is CanonicalTechnical is LegacyTechnical
    assert ContentSeoAgent is not None
    assert GeoReadinessAgent is not None
    assert AiSearchCitationAgent is not None
    assert DirectAnswerAgent is CanonicalDirectAnswer is LegacyDirectAnswer
    assert CroConversionAgent is not None
    assert SeoPillar is SeoPillarModule
