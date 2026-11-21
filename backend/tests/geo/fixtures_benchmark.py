"""Phase 31 — Controlled 14-Scenario GEO Benchmark Environment & Deterministic Provider Fixtures.

Validates GEO behavior deterministically without live API spend across all 14 scenarios:
  1. New brand with little public coverage
  2. Established brand (entity consistency & source coverage)
  3. Brand with inconsistent descriptions
  4. Brand with outdated product information
  5. Brand with strong website content
  6. Brand with weak content
  7. Brand with competitor-heavy citations
  8. Multilingual brand
  9. Local business
 10. Ecommerce brand
 11. No AI API credentials (honest unmeasured states)
 12. One provider unavailable (partial execution)
 13. Same prompt repeated (response variation)
 14. Changed model version (comparability handling)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import httpx

from app.geo.adapters.base import BaseGeoEngineAdapter, EnginePromptRequest, EngineRawResponse
from app.geo.models import GEOTestingMode


class DeterministicGeoProvider(BaseGeoEngineAdapter):
    """Deterministic test adapter honoring the full GEOProvider contract without network calls."""

    def __init__(
        self,
        *,
        engine_id: str,
        display_name: str,
        model: str,
        testing_mode: GEOTestingMode = GEOTestingMode.API_WITH_SEARCH,
        configured: bool = True,
        fail_with_status: Optional[int] = None,
        responses_fn: Optional[Callable[[str, int], tuple[str, List[str]]]] = None,
        cost_per_call_usd: float = 0.01,
    ):
        super().__init__(api_key="test-key" if configured else "", model=model)
        self.engine_id = engine_id
        self.display_name = display_name
        self.default_model = model
        self.default_testing_mode = testing_mode
        self.supports_web_search = testing_mode == GEOTestingMode.API_WITH_SEARCH
        self.supports_citation_metadata = testing_mode == GEOTestingMode.API_WITH_SEARCH
        self.fail_with_status = fail_with_status
        self.responses_fn = responses_fn
        self.cost_per_call_usd = cost_per_call_usd
        self.calls: List[EnginePromptRequest] = []

    async def execute_prompt(
        self,
        request: EnginePromptRequest | Dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> EngineRawResponse:
        req = request if isinstance(request, EnginePromptRequest) else EnginePromptRequest(**request)
        self.calls.append(req)
        if not self.is_configured():
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=self.model,
                requested_model=self.model,
                raw_content="",
                status_code=401,
                error="Missing API key",
                is_live=False,
                testing_mode=self.default_testing_mode,
            )
        if self.fail_with_status:
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=self.model,
                requested_model=self.model,
                raw_content="",
                status_code=self.fail_with_status,
                error=f"Simulated HTTP {self.fail_with_status} provider outage",
                is_live=False,
                testing_mode=self.default_testing_mode,
            )
        text, cits = (
            self.responses_fn(req.prompt, req.repetition_number)
            if self.responses_fn
            else ("Generic response.", [])
        )
        return EngineRawResponse(
            engine_id=self.engine_id,
            engine_name=self.display_name,
            model_version=self.model,
            requested_model=self.model,
            raw_content=text,
            citations=cits,
            status_code=200,
            latency_ms=42.0,
            is_live=True,
            testing_mode=self.default_testing_mode,
            prompt_tokens=120,
            completion_tokens=180,
            estimated_cost_usd=self.cost_per_call_usd,
        )

    async def execute_query(self, prompt: str, locale: str = "en-US", client: Optional[httpx.AsyncClient] = None) -> EngineRawResponse:
        return await self.execute_prompt(EnginePromptRequest(prompt=prompt, locale=locale), client=client)


STRONG_PAGE_HTML = """
<html><head>
<title>AcmeFlow — Automated Workflow & Billing Platform</title>
<meta name="description" content="AcmeFlow automates lead routing, billing, and customer support workflows for B2B teams." />
<link rel="canonical" href="https://acmeflow.io/" />
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"AcmeFlow","url":"https://acmeflow.io/","sameAs":["https://linkedin.com/company/acmeflow"]}
</script>
</head><body>
<h1>AcmeFlow Workflow Automation Platform</h1>
<h2>What is AcmeFlow?</h2>
<p>AcmeFlow is a B2B workflow automation platform designed for SaaS operations teams. Last updated: 2026-10-01. Written by Editorial Team. Pricing starts at $49/month with SOC 2 Type II compliance and 99.95% uptime benchmark across 1,200 customers.</p>
<table><tr><th>Feature</th><th>AcmeFlow</th><th>CompetitorX</th></tr><tr><td>Lead Routing</td><td>Included</td><td>Add-on</td></tr></table>
<h2>Frequently Asked Questions</h2>
<p>How much does AcmeFlow cost? Plans start at $49/month. What are limitations? On-premise deployment is not supported. Who uses AcmeFlow? Mid-market B2B teams.</p>
</body></html>
"""

WEAK_PAGE_HTML = """
<html><head><title>Home</title></head><body>
<h1>Welcome</h1>
<p>We provide the best-in-class, revolutionary, world-class, game-changing synergy solution for everyone.</p>
</body></html>
"""

INCONSISTENT_PAGES = [
    {
        "url": "https://driftbrand.io/",
        "raw_html": '<html><head><title>DriftBrand Analytics</title><meta name="description" content="DriftBrand is a cloud analytics tool."/><script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"DriftBrand Inc.","url":"https://driftbrand.io/"}</script></head><body><h1>DriftBrand Analytics</h1><p>DriftBrand Inc. provides cloud analytics.</p></body></html>',
    },
    {
        "url": "https://driftbrand.io/about",
        "raw_html": '<html><head><title>About DriftSoft Logistics</title><meta name="description" content="DriftSoft Logistics provides freight shipping."/><script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"DriftSoft Logistics LLC","url":"https://driftbrand.io/about"}</script></head><body><h1>About DriftSoft Logistics</h1><p>DriftSoft Logistics ships freight globally.</p></body></html>',
    },
]

OUTDATED_PAGE_HTML = """
<html><head><title>LegacySuite — 2019 Desktop Edition</title></head><body>
<h1>LegacySuite</h1>
<p>LegacySuite offers desktop accounting software with no recent product release notes or pricing table.</p>
</body></html>
"""


def build_benchmark_scenarios() -> Dict[str, Dict[str, Any]]:
    """Return all 14 controlled GEO benchmark scenarios."""
    return {
        "new_brand": {
            "target_url": "https://novastart.io/",
            "brand_name": "NovaStart",
            "industry": "developer observability",
            "products": ["NovaTrace"],
            "competitors": ["Datadog", "New Relic"],
            "seed_pages": [{"url": "https://novastart.io/", "raw_html": STRONG_PAGE_HTML.replace("AcmeFlow", "NovaStart").replace("acmeflow.io", "novastart.io")}],
            "provider_overrides": {
                "perplexity": DeterministicGeoProvider(
                    engine_id="perplexity",
                    display_name="Perplexity Pro",
                    model="sonar",
                    responses_fn=lambda q, r: (
                        "1. Datadog is widely recommended for developer observability.\n2. New Relic is a strong option.",
                        ["https://g2.com/categories/observability", "https://datadoghq.com/product"],
                    ),
                )
            },
        },
        "established_brand": {
            "target_url": "https://acmeflow.io/",
            "brand_name": "AcmeFlow",
            "industry": "workflow automation",
            "products": ["AcmeFlow Core"],
            "competitors": ["Zapier", "Make"],
            "seed_pages": [{"url": "https://acmeflow.io/", "raw_html": STRONG_PAGE_HTML}],
            "provider_overrides": {
                "perplexity": DeterministicGeoProvider(
                    engine_id="perplexity",
                    display_name="Perplexity Pro",
                    model="sonar",
                    responses_fn=lambda q, r: (
                        "1. AcmeFlow is a top recommendation for B2B workflow automation, alongside Zapier and Make. See https://acmeflow.io/ and independent reviews.",
                        ["https://acmeflow.io/", "https://g2.com/products/acmeflow", "https://techcrunch.com/acmeflow-review"],
                    ),
                )
            },
        },
        "inconsistent_descriptions": {
            "target_url": "https://driftbrand.io/",
            "brand_name": "DriftBrand",
            "industry": "cloud analytics",
            "seed_pages": INCONSISTENT_PAGES,
            "provider_overrides": {},
        },
        "outdated_product_info": {
            "target_url": "https://legacysuite.io/",
            "brand_name": "LegacySuite",
            "industry": "accounting software",
            "seed_pages": [{"url": "https://legacysuite.io/", "raw_html": OUTDATED_PAGE_HTML}],
            "provider_overrides": {},
        },
        "strong_content": {
            "target_url": "https://acmeflow.io/",
            "brand_name": "AcmeFlow",
            "industry": "workflow automation",
            "products": ["AcmeFlow Core"],
            "seed_pages": [{"url": "https://acmeflow.io/", "raw_html": STRONG_PAGE_HTML}],
            "provider_overrides": {},
        },
        "weak_content": {
            "target_url": "https://weakcopy.io/",
            "brand_name": "WeakCopy",
            "industry": "business software",
            "seed_pages": [{"url": "https://weakcopy.io/", "raw_html": WEAK_PAGE_HTML}],
            "provider_overrides": {},
        },
        "competitor_heavy_citations": {
            "target_url": "https://challenger.io/",
            "brand_name": "ChallengerCRM",
            "industry": "CRM software",
            "competitors": ["HubSpot", "Salesforce"],
            "seed_pages": [{"url": "https://challenger.io/", "raw_html": STRONG_PAGE_HTML.replace("AcmeFlow", "ChallengerCRM").replace("acmeflow.io", "challenger.io")}],
            "provider_overrides": {
                "perplexity": DeterministicGeoProvider(
                    engine_id="perplexity",
                    display_name="Perplexity Pro",
                    model="sonar",
                    responses_fn=lambda q, r: (
                        "1. HubSpot is the top choice for SMB CRM.\n2. Salesforce leads enterprise CRM.",
                        ["https://g2.com/categories/crm", "https://hubspot.com/crm", "https://forbes.com/advisor/best-crm"],
                    ),
                )
            },
        },
        "multilingual_brand": {
            "target_url": "https://eurocloud.eu/",
            "brand_name": "EuroCloud",
            "industry": "cloud storage",
            "markets": ["DE", "FR"],
            "languages": ["en", "de", "fr"],
            "seed_pages": [{"url": "https://eurocloud.eu/", "raw_html": STRONG_PAGE_HTML.replace("AcmeFlow", "EuroCloud").replace("acmeflow.io", "eurocloud.eu")}],
            "provider_overrides": {
                "chatgpt": DeterministicGeoProvider(
                    engine_id="chatgpt",
                    display_name="ChatGPT (OpenAI)",
                    model="gpt-4o-mini",
                    testing_mode=GEOTestingMode.API_MODEL_ONLY,
                    responses_fn=lambda q, r: ("EuroCloud provides GDPR-compliant storage across Germany and France.", []),
                )
            },
        },
        "local_business": {
            "target_url": "https://austindental.example/",
            "brand_name": "Austin Dental Care",
            "industry": "dental clinic",
            "markets": ["Austin, TX"],
            "seed_pages": [{"url": "https://austindental.example/", "raw_html": STRONG_PAGE_HTML.replace("AcmeFlow", "Austin Dental Care").replace("acmeflow.io", "austindental.example")}],
            "provider_overrides": {},
        },
        "ecommerce_brand": {
            "target_url": "https://trailgear.shop/",
            "brand_name": "TrailGear",
            "industry": "outdoor hiking gear",
            "products": ["Ultralight Tent 2P", "Carbon Trekking Poles"],
            "seed_pages": [{"url": "https://trailgear.shop/", "raw_html": STRONG_PAGE_HTML.replace("AcmeFlow", "TrailGear").replace("acmeflow.io", "trailgear.shop")}],
            "provider_overrides": {},
        },
        "no_credentials": {
            "target_url": "https://acmeflow.io/",
            "brand_name": "AcmeFlow",
            "industry": "workflow automation",
            "seed_pages": [{"url": "https://acmeflow.io/", "raw_html": STRONG_PAGE_HTML}],
            "provider_overrides": {
                "chatgpt": DeterministicGeoProvider(engine_id="chatgpt", display_name="ChatGPT", model="gpt-4o-mini", configured=False),
                "perplexity": DeterministicGeoProvider(engine_id="perplexity", display_name="Perplexity", model="sonar", configured=False),
            },
        },
        "one_provider_unavailable": {
            "target_url": "https://acmeflow.io/",
            "brand_name": "AcmeFlow",
            "industry": "workflow automation",
            "seed_pages": [{"url": "https://acmeflow.io/", "raw_html": STRONG_PAGE_HTML}],
            "provider_overrides": {
                "perplexity": DeterministicGeoProvider(
                    engine_id="perplexity",
                    display_name="Perplexity Pro",
                    model="sonar",
                    responses_fn=lambda q, r: ("AcmeFlow is recommended for workflow automation.", ["https://acmeflow.io/"]),
                ),
                "gemini": DeterministicGeoProvider(
                    engine_id="gemini",
                    display_name="Google Gemini",
                    model="gemini-2.0-flash",
                    fail_with_status=503,
                ),
            },
        },
        "repeated_prompt_variation": {
            "target_url": "https://acmeflow.io/",
            "brand_name": "AcmeFlow",
            "industry": "workflow automation",
            "repetitions": 2,
            "seed_pages": [{"url": "https://acmeflow.io/", "raw_html": STRONG_PAGE_HTML}],
            "provider_overrides": {
                "perplexity": DeterministicGeoProvider(
                    engine_id="perplexity",
                    display_name="Perplexity Pro",
                    model="sonar",
                    responses_fn=lambda q, rep: (
                        ("1. AcmeFlow is recommended for B2B workflow automation.", ["https://acmeflow.io/"])
                        if rep == 1
                        else ("Consider Zapier or Make for workflow automation.", ["https://zapier.com/"])
                    ),
                )
            },
        },
        "changed_model_version": {
            "target_url": "https://acmeflow.io/",
            "brand_name": "AcmeFlow",
            "industry": "workflow automation",
            "seed_pages": [{"url": "https://acmeflow.io/", "raw_html": STRONG_PAGE_HTML}],
            "provider_overrides": {
                "chatgpt": DeterministicGeoProvider(
                    engine_id="chatgpt",
                    display_name="ChatGPT (OpenAI)",
                    model="gpt-4o-2026-08-01",
                    testing_mode=GEOTestingMode.API_MODEL_ONLY,
                    responses_fn=lambda q, r: ("AcmeFlow automates B2B workflows.", []),
                )
            },
        },
    }
