"""Pillar protocol and execution request."""
from app.domain.contracts import DomainPillar, PillarExecutionRequest, PillarId
from app.seo import SeoPillar


def test_seo_pillar_satisfies_the_protocol():
    pillar = SeoPillar()
    assert isinstance(pillar, DomainPillar)
    request = PillarExecutionRequest(pillar_id=PillarId.SEO, wave_index=1, active_agents=["technical_seo"])
    assert request.active_agent_set() == {"technical_seo"}
