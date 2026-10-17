"""Compatibility shim for migrated product intelligence packages.
Transferred to domain modular monoliths:
- geo, citations -> app.geo, app.geo.citations
- aeo -> app.aeo
- cro, accessibility -> app.cro, app.cro.accessibility
- competitive, business, search_demand, serp_tracker -> app.seo
- knowledge, retrieval, indexation -> app.crawl
- monitoring -> app.core.monitoring
- outcomes -> app.domain.commercial
"""
import sys

__path__ = []

from app import geo, aeo, cro, seo, crawl
from app.core import monitoring
from app.geo import citations
from app.seo import competitive, business, search_demand, serp_tracker
from app.crawl import knowledge, retrieval, indexation
from app.domain.commercial import outcomes as commercial_outcomes
from app.cro import accessibility

sys.modules["app.intelligence"] = sys.modules[__name__]
sys.modules["app.intelligence.geo"] = geo
sys.modules["app.intelligence.aeo"] = aeo
sys.modules["app.intelligence.ux"] = cro
sys.modules["app.intelligence.citations"] = citations
sys.modules["app.intelligence.competitive"] = competitive
sys.modules["app.intelligence.business"] = business
sys.modules["app.intelligence.search_demand"] = search_demand
sys.modules["app.intelligence.serp_tracker"] = serp_tracker
sys.modules["app.intelligence.knowledge"] = knowledge
sys.modules["app.intelligence.retrieval"] = retrieval
sys.modules["app.intelligence.indexation"] = indexation
sys.modules["app.intelligence.monitoring"] = monitoring
sys.modules["app.intelligence.accessibility"] = accessibility
import types
outcomes_pkg = types.ModuleType("app.intelligence.outcomes")
outcomes_pkg.__path__ = []
from app.domain.commercial import store as commercial_store, tracking as commercial_tracking
outcomes_pkg.store = commercial_store
outcomes_pkg.tracking = commercial_tracking
sys.modules["app.intelligence.outcomes"] = outcomes_pkg
sys.modules["app.intelligence.outcomes.store"] = commercial_store
sys.modules["app.intelligence.outcomes.tracking"] = commercial_tracking

# Re-export commonly used functions/objects
from app.geo.citations import tracker as citations_tracker
sys.modules["app.intelligence.citations.tracker"] = citations_tracker

