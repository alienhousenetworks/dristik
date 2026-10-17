"""
Crawling & Discovery Agent:
Coordinates native HTTP fetchers, headless browser rendering, robots.txt,
sitemap verification, and multi-page link topology discovery.
"""
from typing import Dict, Any, List, Optional
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType


class CrawlDiscoveryAgent(BaseAgent):
    """
    Discovery Stage Agent responsible for site crawl integrity,
    HTTP status code validation, robots.txt/sitemap discovery, and link topology.
    """
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="discovery.crawler.v3",
            capability="crawling_discovery",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        manifest = getattr(blackboard, "crawl_manifest", None)
        total_pages = len(blackboard.pages) if hasattr(blackboard, "pages") and blackboard.pages else (
            manifest.total_pages_discovered if manifest else 0
        )
        sitemap_found = manifest.sitemap_found if manifest else False
        robots_found = manifest.robots_txt_found if manifest else False
        broken_links = manifest.crawl_health.get("broken_links_count", 0) if (manifest and manifest.crawl_health) else 0

        observations = {
            "total_pages_discovered": total_pages,
            "sitemap_found": sitemap_found,
            "robots_txt_found": robots_found,
            "broken_links_count": broken_links,
        }

        claims = []
        if total_pages == 0:
            claim = self.register_claim(
                blackboard=blackboard,
                statement="No reachable pages discovered during the crawl process.",
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                claim_type=ClaimType.FACT,
                confidence=0.99,
                recommendation="Verify that the domain resolves and is not blocking web crawlers via firewalls or DNS misconfigurations.",
                impact=10,
                effort=3,
            )
            claims.append(claim)
        elif not sitemap_found:
            claim = self.register_claim(
                blackboard=blackboard,
                statement="No XML sitemap was detected at standard locations (/sitemap.xml or referenced in robots.txt).",
                category=Category.TECHNICAL_SEO,
                severity=Severity.MEDIUM,
                claim_type=ClaimType.FACT,
                confidence=0.95,
                recommendation="Publish an XML sitemap and reference its full URL in robots.txt.",
                impact=5,
                effort=2,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "stage": "discovery",
            "perspective": "crawl_topology",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
