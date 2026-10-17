"""
Dristik Domain Pillars: Central registry and domain pillar abstractions.
All 7 domain pillars are authored directly in their respective modular domain packages:
- Crawling: app.crawl.pillar.CrawlingPillar
- SEO: app.seo.pillar.SeoPillar
- GEO: app.geo.pillar.GeoPillar
- AEO: app.aeo.pillar.AeoPillar
- CRO: app.cro.pillar.CroPillar
- Remediation: app.remediation.pillar.RemediationPillar
- Reporting: app.reports.pillar.ReportingPillar
"""
from __future__ import annotations

import sys
import types
from typing import Any, Dict, List, Optional, Set, Type

from app.domain.pillar import PillarId, DomainPillar, PillarScoreResult
from app.domain.pillar_registry import (
    PILLAR_REGISTRY,
    get_pillar,
    list_pillars,
    get_pillar_domains,
    CrawlingPillar,
    SeoPillar,
    GeoPillar,
    AeoPillar,
    CroPillar,
    RemediationPillar,
    ReportingPillar,
)

__all__ = [
    "PILLAR_REGISTRY",
    "get_pillar",
    "list_pillars",
    "get_pillar_domains",
    "PillarId",
    "DomainPillar",
    "PillarScoreResult",
    "CrawlingPillar",
    "SeoPillar",
    "GeoPillar",
    "AeoPillar",
    "CroPillar",
    "RemediationPillar",
    "ReportingPillar",
]

# Backward-compatibility submodule shims for legacy callers
_this_module = sys.modules[__name__]

# 1. app.pillars.registry
_registry_mod = types.ModuleType("app.pillars.registry")
_registry_mod.PILLAR_REGISTRY = PILLAR_REGISTRY
_registry_mod.get_pillar = get_pillar
_registry_mod.list_pillars = list_pillars
_registry_mod.get_pillar_domains = get_pillar_domains
sys.modules["app.pillars.registry"] = _registry_mod

# 2. app.pillars.crawling
_crawling_mod = types.ModuleType("app.pillars.crawling")
_crawling_mod.CrawlingPillar = CrawlingPillar
_crawling_pillar_mod = types.ModuleType("app.pillars.crawling.pillar")
_crawling_pillar_mod.CrawlingPillar = CrawlingPillar
sys.modules["app.pillars.crawling"] = _crawling_mod
sys.modules["app.pillars.crawling.pillar"] = _crawling_pillar_mod

# 3. app.pillars.remediation
_remediation_mod = types.ModuleType("app.pillars.remediation")
_remediation_mod.RemediationPillar = RemediationPillar
_remediation_pillar_mod = types.ModuleType("app.pillars.remediation.pillar")
_remediation_pillar_mod.RemediationPillar = RemediationPillar
sys.modules["app.pillars.remediation"] = _remediation_mod
sys.modules["app.pillars.remediation.pillar"] = _remediation_pillar_mod

# 4. app.pillars.reporting
_reporting_mod = types.ModuleType("app.pillars.reporting")
_reporting_mod.ReportingPillar = ReportingPillar
_reporting_pillar_mod = types.ModuleType("app.pillars.reporting.pillar")
_reporting_pillar_mod.ReportingPillar = ReportingPillar
sys.modules["app.pillars.reporting"] = _reporting_mod
sys.modules["app.pillars.reporting.pillar"] = _reporting_pillar_mod
