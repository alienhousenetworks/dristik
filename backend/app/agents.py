"""
Compatibility re-export from domain modular structures.
Specialist agents are authored directly within their respective domain packages:
- SEO Agents: app.seo.agents
- GEO Agents: app.geo.agents
- AEO Agents: app.aeo
- CRO Agents: app.cro
- Crawl & Discovery: app.crawl.discovery & app.crawl.page_intelligence
- Deck Presentations: app.reports.deck
- Agent Runtime: app.orchestration.runtime
"""
from __future__ import annotations

import sys
import types

__path__: list[str] = []

# Pre-register app.agents.runtime and discovery in sys.modules to prevent circular import errors
from app.orchestration import runtime
from app.orchestration.runtime.base_agent import BaseAgent
from app.orchestration.runtime import base as rt_base
from app.orchestration.runtime import base_agent as rt_base_agent
from app.orchestration.runtime import task_cards as rt_task_cards
from app.orchestration.runtime import registry as rt_registry
from app.orchestration.runtime import specialist as rt_specialist
from app.orchestration.runtime import execution_context as rt_execution_context

sys.modules["app.agents.runtime"] = runtime
sys.modules["app.agents.runtime.base"] = rt_base
sys.modules["app.agents.runtime.base_agent"] = rt_base_agent
sys.modules["app.agents.runtime.task_cards"] = rt_task_cards
sys.modules["app.agents.runtime.registry"] = rt_registry
sys.modules["app.agents.runtime.specialist"] = rt_specialist
sys.modules["app.agents.runtime.execution_context"] = rt_execution_context

from app.orchestration.runtime import reasoner as rt_reasoner
from app.orchestration.runtime import reasoners as rt_reasoners
sys.modules["app.agents.runtime.reasoner"] = rt_reasoner
sys.modules["app.agents.runtime.reasoners"] = rt_reasoners

from app.crawl import discovery
sys.modules["app.agents.discovery"] = discovery
from app.crawl.discovery import crawl_discovery, business_discovery, product_discovery, brand_discovery
sys.modules["app.agents.discovery.crawl_discovery"] = crawl_discovery
sys.modules["app.agents.discovery.business_discovery"] = business_discovery
sys.modules["app.agents.discovery.product_discovery"] = product_discovery
sys.modules["app.agents.discovery.brand_discovery"] = brand_discovery

_brand_shim = types.ModuleType("app.agents.discovery.brand_perspective_agent")
_brand_shim.BrandPerspectiveAgent = brand_discovery.BrandPerspectiveAgent
sys.modules["app.agents.discovery.brand_perspective_agent"] = _brand_shim

_biz_shim = types.ModuleType("app.agents.discovery.business_perspective_agent")
_biz_shim.BusinessPerspectiveAgent = business_discovery.BusinessPerspectiveAgent
sys.modules["app.agents.discovery.business_perspective_agent"] = _biz_shim

_crawl_shim = types.ModuleType("app.agents.discovery.crawl_discovery_agent")
_crawl_shim.CrawlDiscoveryAgent = crawl_discovery.CrawlDiscoveryAgent
sys.modules["app.agents.discovery.crawl_discovery_agent"] = _crawl_shim

_prod_shim = types.ModuleType("app.agents.discovery.product_perspective_agent")
_prod_shim.ProductPerspectiveAgent = product_discovery.ProductPerspectiveAgent
sys.modules["app.agents.discovery.product_perspective_agent"] = _prod_shim

from app.reports import deck
from app.geo import agents as geo_agents
from app.seo import agents as seo_agents
from app.crawl import page_intelligence
from app import aeo as aeo_mod
from app import cro as cro_mod

sys.modules["app.agents.deck"] = deck
sys.modules["app.agents.geo"] = geo_agents
sys.modules["app.agents.seo"] = seo_agents
sys.modules["app.agents.aeo"] = aeo_mod
sys.modules["app.agents.cro"] = cro_mod

_aeo_shim = types.ModuleType("app.agents.aeo.direct_answer_agent")
_aeo_shim.DirectAnswerAgent = getattr(aeo_mod, "DirectAnswerAgent", None)
sys.modules["app.agents.aeo.direct_answer_agent"] = _aeo_shim

_aeo_canon_shim = types.ModuleType("app.agents.aeo.direct_answers")
_aeo_canon_shim.DirectAnswerAgent = getattr(aeo_mod, "DirectAnswerAgent", None)
sys.modules["app.agents.aeo.direct_answers"] = _aeo_canon_shim


_page_mod = types.ModuleType("app.agents.page")
_page_intel_mod = page_intelligence
sys.modules["app.agents.page"] = _page_mod
sys.modules["app.agents.page.intelligence"] = _page_intel_mod

from app.orchestration import legacy as orch_legacy
sys.modules["app.agents.legacy"] = orch_legacy
from app.orchestration.legacy import business as leg_business
sys.modules["app.agents.legacy.business"] = leg_business

__all__ = ["BaseAgent", "runtime", "discovery", "deck", "orch_legacy"]

